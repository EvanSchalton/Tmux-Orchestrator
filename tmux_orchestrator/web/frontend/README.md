# Tmux Orchestrator Web Dashboard

React + TypeScript frontend for the Tmux Orchestrator monitoring dashboard.

## Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## Features

- Real-time agent monitoring dashboard
- Session and window management interface
- Performance metrics visualization
- Command execution interface

## Tech Stack

- React 18 with TypeScript
- Vite for build tooling
- Ant Design UI components
- React Router for navigation
- Axios for API calls
- Zustand for state management

## Development

The app runs on `http://localhost:5173` by default. Make sure the backend API is running on `http://localhost:8000`.

## Project Structure

```
src/
├── components/     # Reusable UI components
├── pages/         # Route page components
├── services/      # API service layer
├── stores/        # State management
└── hooks/         # Custom React hooks
```

## Next Steps

1. Implement the backend API endpoints in FastAPI
2. Add WebSocket support for real-time updates
3. Complete the agent list and session management interfaces
4. Add performance metrics visualization with charts
5. Implement authentication and authorization
