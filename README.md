# Meal Planning Agent System 🍽️

A complete multi-agent AI system for personalized meal planning with recipe generation, shopping lists, and health analysis. Built using **Google ADK Sequential Agent** pattern for automatic workflow orchestration.

## 🌟 Features

- **Sequential Agent Orchestration**: Automatic agent chaining with built-in error handling
- **Preference Agent**: Parse natural language dietary preferences into structured profiles
- **Recipe Agent**: Fetch recipes based on user preferences using Google Search + Gemini AI
- **Shopping & Budget Agent**: Generate itemized shopping lists with live pricing from Amazon Grocery API
- **Health Agent**: Analyze nutrition against user health goals and provide recommendations
- **Memory Service**: Cross-session context and conversation recall

## 🏗️ Architecture

### Sequential Agent Workflow
```
User Input
    ↓
┌─────────────────────────────────────┐
│  Sequential Agent Orchestrator      │
├─────────────────────────────────────┤
│  Step 1: Preference Agent           │
│  → Parse user description           │
│  → Create health profile            │
├─────────────────────────────────────┤
│  Step 2: Recipe Agent               │
│  → Use profile to find recipe       │
│  → Extract ingredients & nutrition  │
├─────────────────────────────────────┤
│  Step 3: Shopping Agent             │
│  → Generate shopping list           │
│  → Fetch live prices                │
└─────────────────────────────────────┘
    ↓
Complete Meal Plan
```

**Why Sequential Agent?**
- ✅ Automatic data flow between agents
- ✅ Built-in error handling and retry logic
- ✅ Automatic session and memory management
- ✅ Cleaner, more maintainable code
- ✅ Better performance (no network overhead vs A2A protocol)

## 📋 API Endpoints

### Main Endpoint (Sequential Agent)
- `POST /complete-meal-plan` - **RECOMMENDED**: Full workflow using Sequential Agent orchestration
- `GET /` - Health check and API information

### Legacy Endpoints (Backward Compatible)
- `POST /complete-meal-plan-legacy` - Old manual chaining approach
- `POST /preference` - Individual preference agent
- `POST /recipe` - Individual recipe agent  
- `POST /shopping` - Individual shopping agent
- `POST /health` - Individual health agent
- `POST /preference-to-recipe` - Preference → Recipe workflow
- `POST /meal-plan` - Recipe → Shopping + Nutrition workflow

### Memory Endpoints
- `POST /memory/save-session` - Save session to memory
- `POST /memory/search` - Search past conversations
- `GET /memory/stats` - Memory statistics

### Individual Agent Endpoints (Legacy)
- `GET /preference/{user_id}` - Retrieve stored user profile
- `GET /recipe/example` - Get example recipe for testing

## 🚀 Quick Start

### 1. Installation

```powershell
# Clone repository
git clone https://github.com/NikzRN01/Agent.git
cd meal_planner_agent

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file:
```
GOOGLE_API_KEY=your_gemini_api_key_here
RAPIDAPI_KEY=your_rapidapi_key_here
```

### 3. Start the Server

```powershell
# Option 1: Using Python
python main.py

# Option 2: Using uvicorn with auto-reload
uvicorn main:app --reload --log-level info
```

Server will start at: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

## 🧪 Testing

### Option 1: Test Sequential Agent Orchestrator (Recommended)
```powershell
# Test the new Sequential Agent workflow
python test_orchestrator.py
```

Choose between interactive or automated mode to test the full orchestration.

### Option 2: API Tests
```powershell
# Terminal 1: Start server
python main.py

# Terminal 2: Run API tests
python test_api.py
```

You'll be prompted to enter your dietary preferences interactively.

### Option 3: Direct Agent Testing (Legacy)
```powershell
python test_integration.py
```

Test individual agents using the old manual chaining approach.

## 📝 Example Usage

### Complete Meal Plan via API

**Request:**
```bash
curl -X POST http://localhost:8000/complete-meal-plan \
  -H "Content-Type: application/json" \
  -d '{
    "user_description": "I am vegetarian, need 2000 calories, 120g protein daily, allergic to peanuts, diabetic",
    "user_id": "user_001"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_profile": {
      "diet_type": "vegetarian",
      "daily_calorie_target": 2000,
      "protein_target_g": 120,
      "allergies": ["peanut"],
      "health_notes": ["low_sugar"]
    },
    "recipe": {
      "recipe_name": "High-Protein Vegetarian Bowl",
      "ingredients": {...},
      "nutritional_information": {...}
    },
    "shopping_plan": {
      "estimated_total_cost": 450.50,
      "currency": "INR",
      "within_budget": true,
      "categorized_items": [...]
    },
    "health_analysis": {
      "daily_targets": {...},
      "recommendations": [...]
    }
  }
}
```

### Using Python Requests

```python
import requests

response = requests.post(
    "http://localhost:8000/complete-meal-plan",
    json={
        "user_description": "Vegan, 1800 calories, high protein, low carb",
        "user_id": "user_123"
    }
)

data = response.json()
print(f"Recipe: {data['data']['recipe']['recipe_name']}")
print(f"Total Cost: ₹{data['data']['shopping_plan']['estimated_total_cost']}")
```

## 🛠️ Technology Stack

- **Framework**: FastAPI (Python 3.13)
- **AI Models**: Google Gemini 2.0 Flash (via Google ADK)
- **Orchestration**: Sequential Agent (Google ADK)
- **Memory**: InMemoryMemoryService (session-based context)
- **Tools**: Google Search API
- **Pricing API**: RapidAPI Amazon Grocery API
- **Data Validation**: Pydantic
- **Server**: Uvicorn

**Configuration:**
- Retry logic: 8 attempts, exponential backoff (base 10), max 60s delay
- Session management: InMemorySessionService
- Memory persistence: Cross-session context (in-memory)

## 📊 Project Structure

```
meal_planner_agent/
├── orchestrator.py             # Sequential Agent orchestrator (NEW)
├── test_orchestrator.py        # Test Sequential Agent workflow (NEW)
├── agents/
│   ├── preference_agent.py     # Preference parsing with Gemini
│   ├── recipe_agent.py         # Recipe generation with Google Search
│   ├── shopping_budget_agent.py # Shopping list + live pricing
│   └── health_agent.py         # Nutrition analysis
├── models/
│   └── schema.py               # Pydantic data models
├── main.py                     # FastAPI server with Sequential Agent
├── test_api.py                 # API endpoint tests (interactive)
├── test_integration.py         # Direct agent tests (legacy)
├── .env                        # API keys (create this)
├── .gitignore                  # Git ignore rules
└── requirements.txt            # Python dependencies
```

**Key Files:**
- `orchestrator.py` - Implements Sequential Agent pattern for automatic workflow
- `test_orchestrator.py` - Tests the orchestrated workflow with memory features
- `main.py` - FastAPI server exposing Sequential Agent via REST API

## 🔑 Required API Keys

### Google API Key (Gemini)
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API key
3. Add to `.env`: `GOOGLE_API_KEY=your_key`

## 🎯 Features in Detail

### 1. Preference Agent
- Parses natural language into structured JSON
- Extracts: diet type, calories, macros, allergies, health conditions
- Interactive completion for missing fields
- Stores profiles in memory (user_id based)

### 2. Recipe Agent
- Google Search integration for real recipes
- Structured JSON output with sections
- Ingredients categorized by cooking stage
- Step-by-step instructions
- Estimated nutritional information

### 3. Shopping & Budget Agent
- Ingredient parsing from recipe format
- Category classification (vegetables, proteins, grains, etc.)
- Live price fetching from Amazon Grocery API
- Fallback to estimated prices when API unavailable
- Budget analysis and recommendations

### 4. Health Agent
- Compares recipe nutrition to user targets
- Per-meal macro calculations
- Health-based recommendations (low sugar, low sodium, etc.)
- Allergy warnings and dietary restrictions

## 🐛 Troubleshooting

### Issue: "GOOGLE_API_KEY not found"
**Solution:** Create `.env` file with your API key

### Issue: "Port 8000 already in use"
**Solution:** 
```powershell
# Find and kill process using port 8000
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Or use different port
uvicorn main:app --port 8001
```

### Issue: "Import errors for agents"
**Solution:** 
```powershell
pip install -r requirements.txt
```

### Issue: "No recipe_data found"
**Solution:** Check internet connection (Google Search requires network access)

### Issue: Rate Limits (429 errors)
**Solution:** The Sequential Agent has enhanced retry logic:
- 8 retry attempts (up from 5)
- Exponential backoff with base 10
- Max delay capped at 60 seconds

### Issue: Memory not persisting
**Note:** Memory is in-memory only (InMemoryMemoryService):
- ✅ Fast and free
- ❌ Data lost on server restart
- For persistence, upgrade to VertexAIMemoryBankService (requires Google Cloud)

## 📈 Future Enhancements

- [ ] Database integration for persistent storage
- [ ] Week-long meal planning
- [ ] Multi-store price comparison
- [ ] Nutritional database integration
- [ ] User authentication and history
- [ ] Mobile app integration
- [ ] Recipe image generation
- [ ] Grocery delivery integration
- [ ] Upgrade to VertexAI Memory for persistent context
- [ ] A2A Protocol for distributed microservices (when needed)

## 📚 Learn More

- **API Documentation**: `http://localhost:8000/docs` (when server running)
- **Sequential Agent Guide**: [Google ADK Sequential Agents](https://google.github.io/adk-docs/agents/workflow-agents/sequential-agents/)
- **Memory Documentation**: [ADK Memory](https://google.github.io/adk-docs/sessions/memory/)
- **A2A vs Sequential**: [When to use A2A vs Local Sub-Agents](https://google.github.io/adk-docs/a2a/intro/#when-to-use-a2a-vs-local-sub-agents)

## 📄 License

MIT License

## 👥 Contributors

- **NikzRN01** - Initial development
- **TJ** - Recipe Agent & Shopping Agent implementation
- **Pratham** - Preference Agent implementation

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📞 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/NikzRN01/Agent/issues)
- Documentation: `http://localhost:8000/docs` (when server running)

---

**Last Updated:** December 2025  
**Status:** ✅ Production Ready