"""
model.py — Arquitectura NeuMF (Neural Collaborative Filtering)

Implementa el modelo NeuMF completo según He et al. (2017):
  - GMF path: captura interacciones lineales (equivalente a MF clásico)
  - MLP path: captura interacciones no lineales mediante capas densas
  - Fusión: concatenación GMF[64] + MLP[32] → Dense(1) + Sigmoid

Referencia: He, X. et al. "Neural Collaborative Filtering." WWW 2017.
"""

import torch
import torch.nn as nn


class NeuMF(nn.Module):
    """
    Neural Matrix Factorization (NeuMF) — GMF + MLP fusionados.

    Args:
        n_users:    Número de usuarios únicos (800 en el dataset actual).
        n_items:    Número de ítems únicos (1843 en el dataset actual).
        k:          Dimensión de los embeddings (default: 64).
        mlp_layers: Tamaños de las capas ocultas del MLP path.
                    Input implícito: 2*k (concatenación de embeddings usuario e ítem).
    """

    def __init__(
        self,
        n_users: int,
        n_items: int,
        k: int = 64,
        mlp_layers: list[int] = None,
    ) -> None:
        super().__init__()

        if mlp_layers is None:
            mlp_layers = [128, 64, 32]

        # ── GMF embeddings ─────────────────────────────────────────────────────
        # Cada usuario e ítem tiene un embedding independiente para el path GMF.
        # El producto elemento a elemento captura afinidades lineales.
        self.gmf_user_emb = nn.Embedding(n_users, k)
        self.gmf_item_emb = nn.Embedding(n_items, k)

        # ── MLP embeddings ─────────────────────────────────────────────────────
        # Embeddings separados para el path MLP permiten que cada componente
        # aprenda representaciones distintas (He et al., sección 3.3).
        self.mlp_user_emb = nn.Embedding(n_users, k)
        self.mlp_item_emb = nn.Embedding(n_items, k)

        # ── MLP layers ─────────────────────────────────────────────────────────
        # Input: Concat[Emb_user, Emb_item] → 2*k = 128 dimensiones
        # Output: mlp_layers[-1] = 32 dimensiones
        mlp_input_size = 2 * k
        layers = []
        in_size = mlp_input_size
        for out_size in mlp_layers:
            layers.append(nn.Linear(in_size, out_size))
            layers.append(nn.ReLU())
            in_size = out_size
        self.mlp = nn.Sequential(*layers)

        # ── Output layer ───────────────────────────────────────────────────────
        # Fusión: GMF[k=64] + MLP_output[32] = 96 dimensiones → escalar
        fusion_size = k + mlp_layers[-1]
        self.output_layer = nn.Linear(fusion_size, 1)

        self._init_weights()

    def _init_weights(self) -> None:
        """Inicialización de pesos siguiendo He et al.: Normal(0, 0.01)."""
        for emb in [
            self.gmf_user_emb, self.gmf_item_emb,
            self.mlp_user_emb, self.mlp_item_emb,
        ]:
            nn.init.normal_(emb.weight, mean=0.0, std=0.01)

        for module in self.mlp.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)

        nn.init.xavier_uniform_(self.output_layer.weight)
        nn.init.zeros_(self.output_layer.bias)

    def forward(
        self,
        user: torch.Tensor,
        item: torch.Tensor,
    ) -> torch.Tensor:
        """
        Forward pass del modelo.

        Args:
            user: Tensor de índices de usuarios  (batch_size,)
            item: Tensor de índices de ítems     (batch_size,)

        Returns:
            Tensor de scores ∈ (0, 1)            (batch_size,)
        """
        # ── GMF path ───────────────────────────────────────────────────────────
        gmf_u = self.gmf_user_emb(user)    # (batch, k)
        gmf_i = self.gmf_item_emb(item)    # (batch, k)
        gmf_out = gmf_u * gmf_i            # (batch, k) — producto elemento a elemento

        # ── MLP path ───────────────────────────────────────────────────────────
        mlp_u = self.mlp_user_emb(user)    # (batch, k)
        mlp_i = self.mlp_item_emb(item)    # (batch, k)
        mlp_concat = torch.cat([mlp_u, mlp_i], dim=1)  # (batch, 2k)
        mlp_out = self.mlp(mlp_concat)     # (batch, 32)

        # ── Fusión y predicción ────────────────────────────────────────────────
        combined = torch.cat([gmf_out, mlp_out], dim=1)    # (batch, k+32 = 96)
        logit = self.output_layer(combined).squeeze(-1)    # (batch,)
        return torch.sigmoid(logit)                        # (batch,) ∈ (0, 1)

    def predict_all(
        self,
        user_idx: int,
        n_items: int,
        device: torch.device,
        batch_size: int = 2048,
    ) -> torch.Tensor:
        """
        Calcula ncf_score para un usuario contra TODOS los ítems.
        Usado en batch_inference.py para el cross-join completo.

        Args:
            user_idx:   Índice entero del usuario.
            n_items:    Número total de ítems.
            device:     CPU o CUDA.
            batch_size: Tamaño de batch para evitar OOM.

        Returns:
            Tensor (n_items,) con scores ∈ (0, 1).
        """
        self.eval()
        scores = []
        user_tensor = torch.tensor([user_idx], device=device)

        with torch.no_grad():
            for start in range(0, n_items, batch_size):
                end = min(start + batch_size, n_items)
                items = torch.arange(start, end, device=device)
                users = user_tensor.expand(end - start)
                score = self.forward(users, items)
                scores.append(score.cpu())

        return torch.cat(scores)  # (n_items,)
