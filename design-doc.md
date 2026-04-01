# NarrativeTrail — Design Document

## Problem Statement
How do political narratives travel and mutate across the ideological spectrum on Reddit?
This dashboard analyzes 8,799 Reddit posts across 10 political communities spanning
far-left to far-right, covering the US 2024 election period (July 2024 - February 2025).

## Case Study Angle
The same topics — immigration, economy, election integrity — appear across all 10
subreddits but with dramatically different framing. NarrativeTrail traces this divergence:
which communities amplified it first, which power users drove it, and how framing mutated.

## System Goals
1. Show how specific topics trend differently across communities over time
2. Identify the most influential accounts and how narratives spread through crossposts
3. Enable semantic search that finds relevant posts without exact keyword matching
4. Cluster posts by topic to reveal the dominant narratives in the dataset

## Feature Decisions
- **Timeline**: time-series because it shows evolution of narratives over 7 months
- **Network**: PageRank because recursive influence matters more than raw connection count
- **Semantic search**: FAISS + sentence-transformers because keyword search fails misinformation research
- **BERTopic over LDA**: transformer embeddings capture semantic meaning, not just word frequency

## What I Rejected
- **Streamlit**: inflexible, signals generic submission
- **KMeans**: requires specifying k, assumes spherical clusters, poor for text
- **Plotly for network**: crashes at scale, not interactive enough
- **Keyword search**: fails SimPPL's zero-overlap query test