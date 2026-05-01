🧠 Wumpus World — Knowledge-Based AI Agent

An intelligent AI simulation of the classic Wumpus World problem, implemented using Python (Flask) and Propositional Logic.
The agent does not rely on guessing — instead, it uses a Knowledge Base with Resolution Refutation to logically infer safe paths, detect dangers, and make decisions in an uncertain environment.

🚀 Project Overview

The Wumpus World is a grid-based environment containing:

🕳 Pits (deadly traps)
👹 Wumpus (dangerous creature)
✨ Gold (goal)

The AI agent starts from a fixed position and must:

Explore the world safely
Avoid pits and Wumpus
Use logic to determine safe moves
Find gold and return home

Instead of random movement, the agent uses logical reasoning (AI Knowledge Base).

🧠 Core Intelligence (AI Logic)

This project implements a Knowledge-Based Agent using:

📌 1. Propositional Logic
Facts are stored in CNF (Conjunctive Normal Form)
Each cell is represented as logical variables:
P(x,y) → Pit
W(x,y) → Wumpus
¬P(x,y) → No Pit
¬W(x,y) → No Wumpus
📌 2. Resolution Refutation
Used to prove whether a cell is safe or dangerous
Works by:
Assuming a statement is true
Deriving contradictions
If contradiction found → statement is false
📌 3. Knowledge Base (KB)

The agent continuously updates KB using percepts:

🌬 Breeze → at least one nearby pit
👃 Stench → Wumpus nearby
✨ Glitter → gold found
❌ No Breeze → all adjacent cells are pit-free
❌ No Stench → no Wumpus nearby
🎮 Features
🧠 AI-based decision making (no random moves)
📊 Real-time Knowledge Base updates
🔍 Resolution-based inference engine
🤖 Auto-play intelligent agent
🗺 Interactive grid visualization
⚠ Safe vs Dangerous cell detection
📜 Event logging system
📈 Live metrics (moves, KB size, inference steps)
🛠 Tech Stack
Backend:
Python 🐍
Flask 🌐
Flask-CORS
Frontend:
HTML5
CSS3 (Modern UI design)
JavaScript (Vanilla)
AI Concepts:
Propositional Logic
CNF (Conjunctive Normal Form)
Resolution Refutation
Knowledge-Based Agents
