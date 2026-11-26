# Enterprise RAG — Local Document Intelligence & Retrieval System

A local-first Enterprise Retrieval-Augmented Generation (RAG) application designed to ingest documents, index their contents, retrieve relevant information, and provide source-based responses through an interactive web interface.

The system combines **FastAPI, LangGraph, SQLite, FAISS, BM25 and React** to provide a document retrieval workspace that runs locally without requiring cloud AI services or hosted vector databases.

> **Project status:** Local retrieval implementation with hybrid BM25 + FAISS search. This is currently a retrieval-focused system, not an LLM-powered answer-generation system.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Hybrid Retrieval](#hybrid-retrieval)
- [Installation and Setup](#installation-and-setup)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Frontend Modules](#frontend-modules)
- [Configuration](#configuration)
- [Testing](#testing)
- [Current Limitations](#current-limitations)
- [Future Improvements](#future-improvements)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Enterprise RAG is a locally executable document retrieval platform that allows users to upload business documents, process their contents, create searchable document chunks, and retrieve relevant information through a chat interface.

The application is designed around local data processing and storage.

Unlike cloud-dependent RAG implementations, this project uses:

- SQLite for application metadata and conversations.
- FAISS for local vector indexing and similarity search.
- BM25 for keyword-based document retrieval.
- Reciprocal Rank Fusion for combining retrieval rankings.
- LangGraph for workflow orchestration.
- FastAPI for backend APIs.
- React and Vite for the frontend.

The current implementation focuses on improving document retrieval accuracy and providing transparent source references.

## Key Features

### 1. Document Management

- Upload PDF, DOCX and TXT documents.
- Extract text from supported document formats.
- Split documents into manageable text chunks.
- Generate local feature-hashing vectors.
- Store document metadata in SQLite.
- Index document vectors using FAISS.
- Delete documents and their associated indexed vectors.

### 2. Hybrid Information Retrieval

The retrieval pipeline combines two approaches:

- **BM25:** Finds relevant passages using keyword matching and term frequency.
- **FAISS:** Retrieves similar passages using local vector representations.
- **Reciprocal Rank Fusion:** Combines the rankings from both retrieval methods.

This approach helps retrieve passages containing important terms, names, identifiers and numerical information.

### 3. RAG Chat Interface

- Ask questions about uploaded documents.
- Retrieve relevant document passages.
- Display source filenames and chunk references.
- Display retrieval relevance information.
- Handle empty retrieval results.
- Maintain conversation references.

The current chat interface returns retrieved document content rather than generating independent natural-language answers using an LLM.

### 4. Human-in-the-Loop Approval

- Identify requests that require human review.
- Maintain approval records.
- Allow reviewers to approve or reject requests.
- Resume supported workflow operations after approval.

### 5. Local Database Management

SQLite stores application metadata, including:

- Document records.
- Conversation records.
- Message records.
- Approval records.
- Audit logs.

LangGraph checkpoint state is maintained using a local SQLite checkpoint database.

### 6. Local-First Execution

- No AWS infrastructure required.
- No Pinecone dependency.
- No Neon or hosted PostgreSQL database.
- No external hosted AI inference API.
- No mandatory cloud deployment.

The backend, frontend, database and retrieval index run on the local machine.

---

## System Architecture

```mermaid
flowchart TD
    A[User] --> B[React Frontend]
    B --> C[FastAPI Backend]

    C --> D[Document Management]
    C --> E[LangGraph Workflow]

    D --> F[Text Extraction]
    F --> G[Text Chunking]
    G --> H[Feature Hashing]
    H --> I[FAISS Vector Index]
   
