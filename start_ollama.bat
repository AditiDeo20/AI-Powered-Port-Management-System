@echo off
set CUDA_VISIBLE_DEVICES=-1
set OLLAMA_LLM_LIBRARY=cpu
ollama serve
