---
type: concept
created: 2026-04-10
updated: 2026-04-10
tags: [architecture, NLP, foundational, LLM]
---

# Transformer

## Definition

基于自注意力机制的神经网络架构，由[[Google Brain]]在2017年论文《Attention Is All You Need》中提出。是现代[[大语言模型]]的标准架构。

## Key Aspects

- 纯注意力架构，取代[[循环神经网络]]
- 并行化训练，大幅提升效率
- 变体：Encoder-only([[BERT]])、Decoder-only([[GPT系列]])、Encoder-Decoder(T5)
- 支撑了GPT-3、ChatGPT、LLaMA等所有主流LLM

## Impact

Transformer的出现彻底改变了NLP领域，并逐渐扩展到计算机视觉([[ViT]])、语音、多模态等领域。

## Related Concepts

- [[注意力机制]] (核心组件)
- [[大语言模型]] (基于Transformer)
- [[GPT系列]] (inferred)
- [[BERT]] (inferred)
- [[Google Brain]] (发明团队)

## Sources

- [[人工智能简史]]
- [[深度学习革命]]
- [[大语言模型前沿]]
