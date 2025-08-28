\# AI-Assistant  

## AI Assistant – Sprint 1  

### Overview  
This repository contains the first sprint implementation of the **AI Assistant**, an intelligent planner and productivity tool. The system integrates an agentic AI architecture with vector search, persistent memory, and external APIs to assist users with scheduling, email, and task management.  

Sprint 1 establishes the foundational infrastructure, including backend and frontend scaffolding, authentication, database setup, and a minimal AI pipeline.  

---

### Sprint 1 Deliverables  

**Backend (FastAPI)**  
- Project structure initialized with FastAPI  
- API routing and middleware configured  

**Database (PostgreSQL + pgvector)**  
- Postgres configured with pgvector extension  
- SQLAlchemy models for user and embedding data implemented  

**Authentication (Supabase)**  
- User sign-up and login with Google session management  
- FastAPI middleware for token verification  

**AI Core (LangChain + GPT-4)**  
- LLM integration via LangChain  
- Initial memory persistence using pgvector  
- Basic conversational endpoint with context retention  

**Frontend (React)**  
- Project scaffolded with React  
- API client established for backend communication  
- Login page and authenticated dashboard shell created  

**Deployment**  
- Frontend deployed to Netlify  
- Backend deployed to Render with PostgreSQL  
- GitHub Actions workflow for linting and build verification  

---

### Technology Stack  
- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, pgvector (through Supabase)  
- **Frontend:** React  
- **AI Layer:** OpenAI GPT-4, LangChain  
- **Authentication:** Google OAuth2  
- **Integrations:** Google Calendar and Gmail APIs (OAuth2)  
- **Deployment:** Netlify (frontend), Render (backend)  
