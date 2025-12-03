# LiveKit AI Voice Agent - Frontend

React-based web interface for the LiveKit AI Voice Agent platform.

## Features

- 🎥 Video conferencing with LiveKit
- 🎤 Real-time audio/video communication
- 🤖 Direct interaction with AI agent
- 🎨 Modern UI with Tailwind CSS
- ⚡ Fast development with Vite

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Open http://localhost:3000

### Production

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

### Docker

```bash
# From project root
docker compose up -d frontend

# Access at http://localhost:3000
```

## Configuration

Set environment variables in `.env` file (project root):

```env
VITE_LIVEKIT_URL=ws://localhost:7880
VITE_API_URL=http://localhost:8000
```

## Usage

1. Enter room name (e.g., `ai-agent-room`)
2. Enter your name
3. Click "Join Room"
4. Allow browser to access microphone/camera
5. Start talking to the AI agent!

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx          # Main application component
│   ├── App.css          # Application styles
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── public/              # Static assets
├── index.html           # HTML template
├── package.json         # Dependencies
├── vite.config.ts       # Vite configuration
├── tailwind.config.js   # Tailwind CSS config
└── tsconfig.json        # TypeScript config
```

## Dependencies

### Core
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool

### LiveKit
- **@livekit/components-react** - React components for LiveKit
- **livekit-client** - LiveKit client SDK
- **@livekit/components-styles** - Pre-built styles

### Styling
- **Tailwind CSS** - Utility-first CSS
- **PostCSS** - CSS processing
- **Autoprefixer** - CSS vendor prefixes

## Development

### Adding New Features

1. **Add Component**:
   ```tsx
   // src/components/NewComponent.tsx
   export function NewComponent() {
     return <div>New Feature</div>
   }
   ```

2. **Use in App**:
   ```tsx
   import { NewComponent } from './components/NewComponent'
   ```

### Environment Variables

Access in code:
```tsx
const apiUrl = import.meta.env.VITE_API_URL
const livekitUrl = import.meta.env.VITE_LIVEKIT_URL
```

### Styling

Use Tailwind CSS classes:
```tsx
<div className="bg-gray-800 p-4 rounded-lg">
  Content
</div>
```

## Building for Production

```bash
# Build
npm run build

# Output in dist/
# Serve with any static file server
```

### Nginx Example

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

## Troubleshooting

### Module Not Found
```bash
rm -rf node_modules package-lock.json
npm install
```

### Port Already in Use
```bash
# Change port in vite.config.ts
server: {
  port: 3001  # Changed from 3000
}
```

### TypeScript Errors
```bash
# Check TypeScript
npm run build

# Fix type errors in .tsx files
```

### LiveKit Connection Issues

1. Check backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Verify LiveKit URL in `.env`:
   ```env
   VITE_LIVEKIT_URL=ws://localhost:7880
   ```

3. Check browser console for errors

4. Ensure token is valid (check Network tab)

## Browser Support

- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+

WebRTC required for audio/video features.

## License

MIT
