# Meal Planning Agent System 🍽️

A complete multi-agent AI system for personalized meal planning with recipe generation, shopping lists, and health analysis.

## 🌟 Features

- **Preference Agent**: Parse natural language dietary preferences into structured profiles
- **Recipe Agent**: Fetch recipes based on user preferences using Google Search + Gemini AI
- **Shopping & Budget Agent**: Generate itemized shopping lists with live pricing from Amazon Grocery API
- **Health Agent**: Analyze nutrition against user health goals and provide recommendations

## 🏗️ Architecture

```
User Input → Preference Agent → Recipe Agent → Shopping Agent
                                             ↓
                                        Health Agent
```

### Complete Workflow
1. User describes preferences in natural language
2. Preference Agent creates structured health profile
3. Recipe Agent fetches personalized recipes
4. Shopping Agent generates categorized shopping list with prices
5. Health Agent provides nutrition analysis and recommendations

## 📋 API Endpoints

### Preference Agent
- `POST /preference` - Create user profile from natural language
- `GET /preference/{user_id}` - Retrieve stored user profile

### Recipe Agent
- `POST /recipe` - Get recipe from structured preferences
- `GET /recipe/example` - Get example recipe for testing

### Shopping & Budget Agent
- `POST /shopping` - Generate shopping list with live pricing

### Health Agent
- `POST /health` - Analyze nutritional information
- `POST /recipe-to-health` - Compare recipe nutrition to user goals

### Complete Workflows
- `POST /complete-meal-plan` - **FULL WORKFLOW**: Preference → Recipe → Shopping + Health
- `POST /preference-to-recipe` - Preference → Recipe workflow
- `POST /meal-plan` - Recipe → Shopping + Nutrition workflow

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

### Option 1: API Tests (Recommended)
```powershell
# Terminal 1: Start server
python main.py

# Terminal 2: Run API tests
python test_api.py
```

You'll be prompted to enter your dietary preferences interactively.

### Option 2: Direct Agent Testing
```powershell
python test_integration.py
```

Choose between interactive or automated mode.

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
- **AI Models**: Google Gemini 2.0 Flash (via ADK)
- **Tools**: Google Search API
- **Pricing API**: RapidAPI Amazon Grocery API
- **Data Validation**: Pydantic
- **Server**: Uvicorn

## 📊 Project Structure

```
meal_planner_agent/
├── agents/
│   ├── preference_agent.py    # Preference parsing with Gemini
│   ├── recipe_agent.py         # Recipe generation with Google Search
│   ├── shopping_budget_agent.py # Shopping list + live pricing
│   └── health_agent.py         # Nutrition analysis
├── models/
│   └── schema.py               # Pydantic data models
├── main.py                     # FastAPI server
├── test_api.py                 # API endpoint tests (interactive)
├── test_integration.py         # Direct agent tests
├── .env                        # API keys (create this)
├── .gitignore                  # Git ignore rules
└── requirements.txt            # Python dependencies
```

## 🔑 Required API Keys

### Google API Key (Gemini)
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API key
3. Add to `.env`: `GOOGLE_API_KEY=your_key`

### RapidAPI Key (Amazon Grocery)
1. Sign up at [RapidAPI](https://rapidapi.com/)
2. Subscribe to [Amazon Grocery API](https://rapidapi.com/grocery-api2/api/grocery-api2)
3. Add to `.env`: `RAPIDAPI_KEY=your_key`

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

## 📈 Future Enhancements

- [ ] Database integration for persistent storage
- [ ] Week-long meal planning
- [ ] Multi-store price comparison
- [ ] Nutritional database integration
- [ ] User authentication and history
- [ ] Mobile app integration
- [ ] Recipe image generation
- [ ] Grocery delivery integration

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

**Version:** 2.0.0  
**Last Updated:** December 2025  
**Status:** ✅ Production Ready