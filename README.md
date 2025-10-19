# MedChat

An RAG-based AI Agent for Intelligent Medical Information Retrieval, designed to support medical students.

## Table of Contents

  - [Overview](https://www.google.com/search?q=%23overview)
  - [The Problem](https://www.google.com/search?q=%23the-problem)
  - [Our Solution: MedChat](https://www.google.com/search?q=%23our-solution-medchat)
  - [Key Features](https://www.google.com/search?q=%23key-features)
  - [Knowledge Base: Data Sources](https://www.google.com/search?q=%23knowledge-base-data-sources)
  - [Project Execution](https://www.google.com/search?q=%23project-execution)

## Overview

MedChat is an AI-powered agent designed to help medical students navigate the vast world of medical literature. Aimed at both early-year students and clinical interns, MedChat provides rapid, accurate, and verifiable answers to medical queries by directly referencing a curated library of trusted textbooks.

## The Problem

Medical students, from their early coursework to clinical internships, face a significant challenge: **information overload**.

  - **For Junior Students:** The sheer volume of medical literature makes it difficult and time-consuming to find specific information needed for their studies.
  - **For Interns:** During hospital rotations, quick and reliable access to information from multiple sources is crucial for reviewing patient records and formulating diagnoses.

MedChat replaces the fragmented, manual process of searching through physical textbooks and scattered online notes with an automated, reliable, and verifiable platform.

## Our Solution: MedChat

We propose **MedChat**, an AI-powered RAG (Retrieval-Augmented Generation) Agent capable of answering medical queries with precise, context-aware, and source-referenced responses. The final deliverable is an intelligent platform that streamlines medical information retrieval.

### Key Features

  - **Advanced Retrieval:** Implements a hybrid search approach combining dense vector retrieval with keyword-based search (BM25) for high accuracy and relevance.
  - **Multi-LLM Support:** Flexible integration with leading Large Language Models (LLMs) such as Google Gemini, OpenAI GPT, and Mistral.
  - **High-Performance Vector Database:** Utilizes **Qdrant** for its efficient performance, scalability, and built-in support for hybrid search functionalities.
  - **Intelligent Memory:** Incorporates both short-term and long-term memory to maintain conversational context and provide a seamless user experience.

## Knowledge Base: Data Sources

Our knowledge base is built upon a curated collection of raw medical textbooks, ensuring all responses are grounded in evidence-based literature.

1.  **Nelson's Pediatric Antimicrobial Therapy (28th ed.)** - *American Academy of Pediatrics (AAP)*
2.  **Bài giảng sản phụ khoa tập 1 (Obstetrics and Gynecology Lecture Vol. 1)** - *Hanoi Medical School*
3.  **Basic & Clinical Pharmacology (14th ed.)** - *McGraw-Hill Companies*
4.  **Bệnh Học Ngoại Khoa Y4 – YHN (Surgical Pathology for 4th-year Medical Students)** - *Hanoi Medical University*
5.  **Clinical Epidemiology: The Essentials (5th ed.)** - *Lippincott Williams & Wilkins*
6.  **CURRENT Medical Diagnosis and Treatment 2025 (64th ed.)** - *McGraw Hill Medical*
7.  **Goodman & Gilman’s The Pharmacological Basis of Therapeutics (14th ed.)**

## Project Execution

To ensure effective project execution, the team is divided into three functional groups:

  - **Front-end:** Responsible for UI/UX design, web application development, and user authentication.
      - *(All members involved)*
  - **Data Processing:** Manages the end-to-end data ingestion pipeline, including optimizing chunking strategies and ensuring data quality in the vector database.
      - *(Luong Tran Sang, Nguyen Thi Bao Tien, Ngo Thanh An, Nguyen Ngoc Han)*
  - **AI Agent:** Develops the core agent, integrates LLMs, and fine-tunes the retrieval and response generation workflow.
      - *(Luong Tran Sang, Pham Minh Hieu)*
