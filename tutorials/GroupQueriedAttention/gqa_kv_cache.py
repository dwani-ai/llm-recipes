import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class GroupedQueryAttentionWithCache(nn.Module):
    """
    Grouped Query Attention (GQA) with KV cache support for efficient autoregressive generation.
    
    Args:
        embed_dim: Total embedding dimension
        num_heads: Number of query heads
        num_kv_heads: Number of key/value heads (groups). Must divide num_heads.
        head_dim: Dimension per head (defaults to embed_dim // num_heads)
        dropout: Dropout probability
        bias: Whether to use bias in linear projections
    """
    def __init__(
        self,
        embed_dim: int,
        num_heads: int,
        num_kv_heads: int,
        head_dim: int = None,
        dropout: float = 0.0,
        bias: bool = True,
    ):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = head_dim or (embed_dim // num_heads)
        self.dropout_p = dropout

        assert embed_dim % num_heads == 0
        assert num_heads % num_kv_heads == 0, "num_heads must be divisible by num_kv_heads"

        # Projections
        self.q_proj = nn.Linear(embed_dim, num_heads * self.head_dim, bias=bias)
        self.k_proj = nn.Linear(embed_dim, num_kv_heads * self.head_dim, bias=bias)
        self.v_proj = nn.Linear(embed_dim, num_kv_heads * self.head_dim, bias=bias)
        self.out_proj = nn.Linear(num_heads * self.head_dim, embed_dim, bias=bias)

        self.repeat_factor = num_heads // num_kv_heads

    def forward(
        self,
        x: torch.Tensor,                        # [batch, seq_len, embed_dim]
        past_key_value: tuple[torch.Tensor, torch.Tensor] | None = None,  # (past_k, past_v)
        position_ids: torch.Tensor | None = None,               # Optional for RoPE [batch, seq_len]
        attn_mask: torch.Tensor | None = None,                  # Optional extra mask
        is_causal: bool = True,                                 # Usually True for generation
        return_weights: bool = False,
    ):
        b, s, _ = x.shape

        # Project queries, keys, values
        q = self.q_proj(x)   # [b, s, num_heads * head_dim]
        k = self.k_proj(x)   # [b, s, num_kv_heads * head_dim]
        v = self.v_proj(x)   # [b, s, num_kv_heads * head_dim]

        # Reshape
        q = q.view(b, s, self.num_heads, self.head_dim)          # [b, s, nq, d]
        k = k.view(b, s, self.num_kv_heads, self.head_dim)       # [b, s, nkv, d]
        v = v.view(b, s, self.num_kv_heads, self.head_dim)       # [b, s, nkv, d]

        # Handle KV cache: append new k/v if cache exists (decode mode)
        if past_key_value is not None:
            past_k, past_v = past_key_value
            k = torch.cat([past_k, k], dim=1)   # [b, past_s + s, nkv, d]
            v = torch.cat([past_v, v], dim=1)
            new_past_key_value = (k, v)
        else:
            new_past_key_value = (k, v)

        current_seq_len = k.shape[1]   # total length after append (prefill or decode)

        # Repeat K and V to match query heads
        k = k.repeat_interleave(self.repeat_factor, dim=2)   # [b, total_s, num_heads, d]
        v = v.repeat_interleave(self.repeat_factor, dim=2)

        # Transpose for attention: [b, heads, seq, d]
        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        # Scaled dot-product attention
        attn_weights = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)

        # Causal mask (for generation / training)
        if is_causal:
            causal_mask = torch.triu(
                torch.full((current_seq_len, current_seq_len), float("-inf"), device=x.device),
                diagonal=1
            )
            # Broadcast to [b, heads, q_len, kv_len] — but since q_len == s (new tokens)
            # In decode mode s=1, so we only mask future for the new position
            causal_mask = causal_mask[None, None, -s:, :]   # only last s positions need full mask
            attn_weights = attn_weights + causal_mask

        # Optional extra mask (e.g. padding)
        if attn_mask is not None:
            attn_weights = attn_weights + attn_mask

        attn_weights = F.softmax(attn_weights, dim=-1)
        if self.dropout_p > 0 and self.training:
            attn_weights = F.dropout(attn_weights, p=self.dropout_p)

        # Output
        out = torch.matmul(attn_weights, v)               # [b, heads, s, d]
        out = out.transpose(1, 2).contiguous().view(b, s, -1)  # [b, s, embed_dim]
        out = self.out_proj(out)

        if return_weights:
            return out, new_past_key_value, attn_weights
        return out, new_past_key_value


# ────────────────────────────────────────────────────────────────
#   Example: autoregressive generation loop (toy usage)
# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(0)

    batch_size, embed_dim = 2, 512
    num_heads, num_kv_heads = 8, 2   # GQA with 4 query heads sharing each KV head
    max_new_tokens = 10

    model = GroupedQueryAttentionWithCache(
        embed_dim=embed_dim,
        num_heads=num_heads,
        num_kv_heads=num_kv_heads,
        dropout=0.0,
    ).to(device)

    # Simulate input token embeddings (in real model: from embedding + RoPE)
    input_ids = torch.randint(0, 1000, (batch_size, 1), device=device)  # dummy
    x = torch.randn(batch_size, 1, embed_dim, device=device)           # current token emb

    past_kv = None   # start with no cache (prefill or first token)

    generated = []
    for step in range(max_new_tokens):
        out, past_kv = model(
            x,
            past_key_value=past_kv,
            is_causal=True,
        )
        # In real model: out → logits → sample next token → update x with new emb
        generated.append(out)   # dummy

        print(f"Step {step+1}: output shape {out.shape}, cache seq_len {past_kv[0].shape[1]}")

    print("Generation complete. Final cache length:", past_kv[0].shape[1])