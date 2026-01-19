import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class GroupedQueryAttention(nn.Module):
    """
    Grouped Query Attention (GQA) module.
    
    - num_heads          : total number of query heads (e.g. 32)
    - num_kv_heads       : number of key/value heads (e.g. 8) → groups = num_heads // num_kv_heads
    - head_dim           : dimension per head (e.g. 128) → embed_dim = num_heads * head_dim
    - For full MHA: set num_kv_heads = num_heads
    - For pure MQA: set num_kv_heads = 1
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

        assert embed_dim % num_heads == 0, "embed_dim must be divisible by num_heads"
        assert num_heads % num_kv_heads == 0, "num_heads must be divisible by num_kv_heads"

        # Projections (Q gets full size, K/V get reduced size)
        self.q_proj = nn.Linear(embed_dim, num_heads * self.head_dim, bias=bias)
        self.k_proj = nn.Linear(embed_dim, num_kv_heads * self.head_dim, bias=bias)
        self.v_proj = nn.Linear(embed_dim, num_kv_heads * self.head_dim, bias=bias)
        
        # Output projection
        self.out_proj = nn.Linear(num_heads * self.head_dim, embed_dim, bias=bias)

    def forward(
        self,
        x: torch.Tensor,                     # [batch, seq_len, embed_dim]
        attn_mask: torch.Tensor = None,      # optional [batch, 1, tgt_len, src_len] or causal
        is_causal: bool = False,
        return_weights: bool = False,
    ):
        b, s, _ = x.shape

        # Project → Q: [b, s, num_heads * head_dim]
        #           K,V: [b, s, num_kv_heads * head_dim]
        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)

        # Reshape → [b, s, heads, head_dim]
        q = q.view(b, s, self.num_heads, self.head_dim)
        k = k.view(b, s, self.num_kv_heads, self.head_dim)
        v = v.view(b, s, self.num_kv_heads, self.head_dim)

        # For GQA: repeat K and V so each query head group sees the same K/V head
        # → expands num_kv_heads → num_heads
        repeat_factor = self.num_heads // self.num_kv_heads
        k = k.repeat_interleave(repeat_factor, dim=2)   # → [b, s, num_heads, head_dim]
        v = v.repeat_interleave(repeat_factor, dim=2)

        # Transpose for attention computation → [b, heads, s, head_dim]
        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        # Scaled dot-product attention
        # (You can replace with torch.nn.functional.scaled_dot_product_attention for speed)
        attn_weights = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)

        if is_causal:
            # Create causal mask if needed (upper triangle = -inf)
            causal_mask = torch.triu(
                torch.full((s, s), float("-inf"), device=x.device), diagonal=1
            )
            attn_weights = attn_weights + causal_mask[None, None, :, :]

        if attn_mask is not None:
            attn_weights = attn_weights + attn_mask

        attn_weights = F.softmax(attn_weights, dim=-1)
        if self.dropout_p > 0 and self.training:
            attn_weights = F.dropout(attn_weights, p=self.dropout_p)

        # Apply attention → [b, heads, s, head_dim]
        out = attn_weights @ v

        # Reshape back → [b, s, num_heads * head_dim]
        out = out.transpose(1, 2).contiguous().view(b, s, -1)

        # Final projection
        out = self.out_proj(out)

        if return_weights:
            return out, attn_weights
        return out


# Example usage
if __name__ == "__main__":
    torch.manual_seed(0)
    batch_size, seq_len, embed_dim = 2, 64, 512
    num_heads = 8
    num_kv_heads = 2   # → 4 query heads share each KV head

    x = torch.randn(batch_size, seq_len, embed_dim, device="cuda" if torch.cuda.is_available() else "cpu")
    
    gqa = GroupedQueryAttention(
        embed_dim=embed_dim,
        num_heads=num_heads,
        num_kv_heads=num_kv_heads,
        dropout=0.1,
    ).to(x.device)
    
    out = gqa(x, is_causal=True)
    print(out.shape)          # torch.Size([2, 64, 512])