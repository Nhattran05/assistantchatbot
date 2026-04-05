# LiveKit Room Connection Guide: Technical Deep Dive

## Table of Contents
1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Component Breakdown](#component-breakdown)
4. [Token Authentication Flow](#token-authentication-flow)
5. [Connection Sequence](#connection-sequence)
6. [Session Management](#session-management)
7. [Code Examples](#code-examples)
8. [Configuration Reference](#configuration-reference)
9. [Troubleshooting](#troubleshooting)

---

## Introduction

This guide provides a detailed technical walkthrough of how the LiveKit `agent-starter-react` repository connects a React frontend to a LiveKit room with a voice agent server. We'll explore the authentication flow, connection sequence, and session management with code examples.

**Repository:** https://github.com/livekit-examples/agent-starter-react

**Tech Stack:**
- **Frontend:** Next.js 15, React 19, TypeScript
- **LiveKit SDK:** `livekit-client`, `@livekit/components-react`
- **Server SDK:** `livekit-server-sdk` (for token generation)
- **UI Framework:** Tailwind CSS, Shadcn UI, Agents UI components

---

## Architecture Overview

The LiveKit connection architecture follows a client-server-room pattern:

```
┌─────────────┐          ┌──────────────┐          ┌─────────────┐
│   Browser   │          │  Next.js API │          │  LiveKit    │
│   (React)   │  ◄─────► │   /api/token │  ◄─────► │   Server    │
└─────────────┘          └──────────────┘          └─────────────┘
      │                                                     │
      │                                                     │
      └─────────────────── WebSocket RTC ──────────────────┘
                          (Media Streaming)
```

### Key Architectural Layers:

1. **Application Layer** (`app/page.tsx`, `components/app/`)
   - Entry point and view management
   - Theme provider and UI state management

2. **Session Layer** (`components/agents-ui/`)
   - AgentSessionProvider: Manages LiveKit session context
   - useSession hook: Connection state management

3. **Token Layer** (`app/api/token/route.ts`)
   - JWT token generation for authentication
   - Room configuration and permissions setup

4. **LiveKit SDK Layer**
   - TokenSource: Abstract token retrieval
   - Room: WebRTC connection and media handling

---

## Component Breakdown

### 1. App Entry Point (`app/page.tsx`)

```typescript
import { headers } from 'next/headers';
import { App } from '@/components/app/app';
import { getAppConfig } from '@/lib/utils';

export default async function Page() {
  const hdrs = await headers();
  const appConfig = await getAppConfig(hdrs);

  return <App appConfig={appConfig} />;
}
```

**Purpose:** Server-side page that fetches configuration and renders the main App component.

### 2. Main Application Component (`components/app/app.tsx`)

```typescript
'use client';

import { useMemo } from 'react';
import { TokenSource } from 'livekit-client';
import { useSession } from '@livekit/components-react';

export function App({ appConfig }: AppProps) {
  // Create token source - either sandbox or local API endpoint
  const tokenSource = useMemo(() => {
    return typeof process.env.NEXT_PUBLIC_CONN_DETAILS_ENDPOINT === 'string'
      ? getSandboxTokenSource(appConfig)
      : TokenSource.endpoint('/api/token');
  }, [appConfig]);

  // Initialize session with token source
  const session = useSession(
    tokenSource,
    appConfig.agentName ? { agentName: appConfig.agentName } : undefined
  );

  return (
    <AgentSessionProvider session={session}>
      <AppSetup />
      <main className="grid h-svh grid-cols-1 place-content-center">
        <ViewController appConfig={appConfig} />
      </main>
      <StartAudioButton label="Start Audio" />
      <Toaster />
    </AgentSessionProvider>
  );
}
```

**Key Features:**
- Creates `TokenSource` for authentication
- Initializes `useSession` hook with token source
- Wraps children with `AgentSessionProvider` for context
- Manages audio startup and notifications

### 3. View Controller (`components/app/view-controller.tsx`)

```typescript
export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start } = useSessionContext();
  const { resolvedTheme } = useTheme();

  return (
    <AnimatePresence mode="wait">
      {/* Welcome view before connection */}
      {!isConnected && (
        <MotionWelcomeView
          key="welcome"
          startButtonText={appConfig.startButtonText}
          onStartCall={start}  // Triggers connection
        />
      )}
      
      {/* Session view after connection */}
      {isConnected && (
        <MotionSessionView
          key="session-view"
          supportsChatInput={appConfig.supportsChatInput}
          supportsVideoInput={appConfig.supportsVideoInput}
          supportsScreenShare={appConfig.supportsScreenShare}
          // ... other props
        />
      )}
    </AnimatePresence>
  );
}
```

**Purpose:** Manages transitions between welcome screen and active session based on connection state.

### 4. Agent Session Provider (`components/agents-ui/agent-session-provider.tsx`)

```typescript
export function AgentSessionProvider({
  session,
  children,
  ...roomAudioRendererProps
}: AgentSessionProviderProps) {
  return (
    <SessionProvider session={session}>
      {children}
      <RoomAudioRenderer {...roomAudioRendererProps} />
    </SessionProvider>
  );
}
```

**Purpose:** 
- Wraps SessionProvider from LiveKit components
- Adds RoomAudioRenderer for audio playback
- Provides session context to all child components

---

## Token Authentication Flow

### Overview

LiveKit uses JWT (JSON Web Token) for authentication. The token contains:
- **Identity:** Unique participant identifier
- **Room Name:** Which room to join
- **Permissions:** VideoGrant (publish/subscribe capabilities)
- **Room Configuration:** Agent dispatch settings

### Token Generation API (`app/api/token/route.ts`)

```typescript
import { AccessToken, type VideoGrant } from 'livekit-server-sdk';
import { RoomConfiguration } from '@livekit/protocol';

const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;

export async function POST(req: Request) {
  // Parse room config from request body
  const body = await req.json();
  const roomConfig = RoomConfiguration.fromJson(
    body?.room_config, 
    { ignoreUnknownFields: true }
  );

  // Generate unique identifiers
  const participantName = 'user';
  const participantIdentity = `voice_assistant_user_${Math.floor(Math.random() * 10_000)}`;
  const roomName = `voice_assistant_room_${Math.floor(Math.random() * 10_000)}`;

  // Create participant token
  const participantToken = await createParticipantToken(
    { identity: participantIdentity, name: participantName },
    roomName,
    roomConfig
  );

  // Return connection details
  return NextResponse.json({
    serverUrl: LIVEKIT_URL,
    roomName,
    participantName,
    participantToken,
  });
}
```

### Token Creation Function

```typescript
function createParticipantToken(
  userInfo: AccessTokenOptions,
  roomName: string,
  roomConfig: RoomConfiguration
): Promise<string> {
  // Initialize AccessToken with API credentials
  const at = new AccessToken(API_KEY, API_SECRET, {
    ...userInfo,
    ttl: '15m',  // Token expires in 15 minutes
  });

  // Define permissions
  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,      // Can send audio/video
    canPublishData: true,   // Can send data messages
    canSubscribe: true,     // Can receive audio/video
  };
  at.addGrant(grant);

  // Add room configuration (for agent dispatch)
  if (roomConfig) {
    at.roomConfig = roomConfig;
  }

  return at.toJwt();  // Convert to JWT string
}
```

### VideoGrant Permissions

| Permission | Description |
|------------|-------------|
| `room` | Room name to join |
| `roomJoin` | Allow joining the room |
| `canPublish` | Can publish audio/video tracks |
| `canPublishData` | Can send data messages |
| `canSubscribe` | Can subscribe to other participants' tracks |

---

## Connection Sequence

### Step-by-Step Flow

```
User Action → Token Request → Room Join → Agent Dispatch → Media Streaming
```

#### **Step 1: User Clicks "Start Call"**

```typescript
// In WelcomeView component
<Button onClick={onStartCall}>
  {startButtonText}
</Button>

// onStartCall is the `start` function from useSessionContext
const { start } = useSessionContext();
```

#### **Step 2: Session Hook Initiates Connection**

The `useSession` hook from `@livekit/components-react`:

```typescript
const session = useSession(
  TokenSource.endpoint('/api/token'),  // Token source
  { agentName: 'my-agent' }            // Optional config
);
```

**What happens internally:**
1. `useSession` prepares to connect
2. When `start()` is called, it requests a token from the TokenSource
3. TokenSource sends POST request to `/api/token`

#### **Step 3: Token Request to API**

```typescript
// TokenSource.endpoint internally does:
fetch('/api/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    room_config: {
      agents: [{ agent_name: 'my-agent' }]  // If agentName provided
    }
  })
})
```

#### **Step 4: API Returns Connection Details**

Response format:
```json
{
  "serverUrl": "wss://your-project.livekit.cloud",
  "roomName": "voice_assistant_room_1234",
  "participantName": "user",
  "participantToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### **Step 5: LiveKit Room Connection**

The `useSession` hook uses the connection details to:

1. **Create Room instance:**
```typescript
const room = new Room({
  adaptiveStream: true,
  dynacast: true,
  // ... other options
});
```

2. **Connect to LiveKit server:**
```typescript
await room.connect(
  serverUrl,        // "wss://your-project.livekit.cloud"
  participantToken  // JWT token
);
```

3. **WebSocket Connection Established:**
   - WebRTC signaling begins
   - ICE candidates exchanged
   - Media tracks negotiated

#### **Step 6: Agent Dispatch (Server-Side)**

If `room_config` contains agent dispatch configuration:

```typescript
room_config: {
  agents: [{ agent_name: 'my-agent' }]
}
```

LiveKit server automatically:
1. Detects the agent configuration
2. Dispatches a job to the specified agent
3. Agent connects to the same room
4. Agent begins processing audio/video

#### **Step 7: Media Streaming Begins**

Once connected:
- User's microphone → LiveKit server → Agent
- Agent's audio output → LiveKit server → User
- Real-time bidirectional audio streaming

### Connection State Management

```typescript
const {
  isConnected,     // Boolean: connection status
  isConnecting,    // Boolean: currently connecting
  start,           // Function: initiate connection
  disconnect,      // Function: terminate connection
  room,            // Room instance
  // ... other session properties
} = useSessionContext();
```

---

## Session Management

### Session Lifecycle

```
Idle → Connecting → Connected → Disconnecting → Disconnected
```

### State Transitions in ViewController

```typescript
export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start } = useSessionContext();

  return (
    <AnimatePresence mode="wait">
      {/* State: Idle/Disconnected */}
      {!isConnected && (
        <WelcomeView onStartCall={start} />
      )}
      
      {/* State: Connected */}
      {isConnected && (
        <AgentSessionView_01
          supportsChatInput={appConfig.supportsChatInput}
          supportsVideoInput={appConfig.supportsVideoInput}
          supportsScreenShare={appConfig.supportsScreenShare}
          isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
        />
      )}
    </AnimatePresence>
  );
}
```

### Media Track Management

Once connected, the session manages:

**1. Local Tracks (User's media):**
```typescript
// Microphone
const microphoneTrack = await room.localParticipant.setMicrophoneEnabled(true);

// Camera (if supported)
if (appConfig.supportsVideoInput) {
  const cameraTrack = await room.localParticipant.setCameraEnabled(true);
}

// Screen share (if supported)
if (appConfig.supportsScreenShare) {
  const screenTrack = await room.localParticipant.setScreenShareEnabled(true);
}
```

**2. Remote Tracks (Agent's audio):**
```typescript
// Automatically subscribed to via RoomAudioRenderer
<RoomAudioRenderer volume={1.0} muted={false} />
```

### Agent State Management

The session tracks agent-specific states:

```typescript
// From useAgentState hook
const {
  state,              // 'initializing' | 'listening' | 'thinking' | 'speaking'
  transcription,      // Current transcription text
  agentAudioTrack,    // Agent's audio track
  // ...
} = useAgentState();
```

### Chat and Transcription

```typescript
// Messages are sent via data channel
room.localParticipant.publishData(
  JSON.stringify({ type: 'chat', message: 'Hello' }),
  { reliable: true }
);

// Transcriptions received from agent
room.on('dataReceived', (payload) => {
  const data = JSON.parse(payload);
  if (data.type === 'transcription') {
    // Update UI with transcription
  }
});
```

---

## Code Examples

### Example 1: Basic Connection Setup

```typescript
import { TokenSource } from 'livekit-client';
import { useSession } from '@livekit/components-react';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';

function MyApp() {
  // Create token source
  const tokenSource = TokenSource.endpoint('/api/token');
  
  // Initialize session
  const session = useSession(tokenSource);
  
  return (
    <AgentSessionProvider session={session}>
      <MyComponents />
    </AgentSessionProvider>
  );
}
```

### Example 2: Connection with Agent Dispatch

```typescript
function MyApp() {
  const tokenSource = TokenSource.endpoint('/api/token');
  
  // Specify agent name for explicit dispatch
  const session = useSession(tokenSource, {
    agentName: 'customer-service-agent'
  });
  
  return (
    <AgentSessionProvider session={session}>
      <MyComponents />
    </AgentSessionProvider>
  );
}
```

### Example 3: Custom Token Source (Sandbox)

```typescript
function getSandboxTokenSource(appConfig: AppConfig) {
  return TokenSource.custom(async () => {
    const url = new URL(
      process.env.NEXT_PUBLIC_CONN_DETAILS_ENDPOINT!,
      window.location.origin
    );
    
    const roomConfig = appConfig.agentName
      ? { agents: [{ agent_name: appConfig.agentName }] }
      : undefined;

    const res = await fetch(url.toString(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Sandbox-Id': appConfig.sandboxId ?? '',
      },
      body: JSON.stringify({ room_config: roomConfig }),
    });
    
    return await res.json();
  });
}
```

### Example 4: Handling Connection States

```typescript
function MyComponent() {
  const { isConnected, isConnecting, error, start, disconnect } = useSessionContext();
  
  if (error) {
    return <div>Error: {error.message}</div>;
  }
  
  if (isConnecting) {
    return <div>Connecting...</div>;
  }
  
  if (!isConnected) {
    return <button onClick={start}>Connect</button>;
  }
  
  return (
    <div>
      <p>Connected!</p>
      <button onClick={disconnect}>Disconnect</button>
    </div>
  );
}
```

### Example 5: Media Control

```typescript
function MediaControls() {
  const { room } = useSessionContext();
  const [micEnabled, setMicEnabled] = useState(true);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  
  const toggleMic = async () => {
    if (room) {
      await room.localParticipant.setMicrophoneEnabled(!micEnabled);
      setMicEnabled(!micEnabled);
    }
  };
  
  const toggleCamera = async () => {
    if (room) {
      await room.localParticipant.setCameraEnabled(!cameraEnabled);
      setCameraEnabled(!cameraEnabled);
    }
  };
  
  return (
    <div>
      <button onClick={toggleMic}>
        {micEnabled ? 'Mute' : 'Unmute'}
      </button>
      <button onClick={toggleCamera}>
        {cameraEnabled ? 'Stop Camera' : 'Start Camera'}
      </button>
    </div>
  );
}
```

---

## Configuration Reference

### Environment Variables (`.env.local`)

```bash
# Required: LiveKit server credentials
LIVEKIT_API_KEY=<your_api_key>
LIVEKIT_API_SECRET=<your_api_secret>
LIVEKIT_URL=wss://<project-subdomain>.livekit.cloud

# Optional: Agent dispatch
# Leave blank for automatic dispatch
# Provide a name for explicit dispatch to a specific agent
AGENT_NAME=

# Internal (for sandbox deployments)
NEXT_PUBLIC_APP_CONFIG_ENDPOINT=
SANDBOX_ID=
```

### App Configuration (`app-config.ts`)

```typescript
export interface AppConfig {
  // Branding
  companyName: string;
  pageTitle: string;
  pageDescription: string;
  logo: string;
  logoDark?: string;
  accent?: string;           // Primary color (light mode)
  accentDark?: string;       // Primary color (dark mode)
  
  // Features
  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;
  
  // UI
  startButtonText: string;
  
  // Audio visualization
  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: string;
  audioVisualizerColorDark?: string;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;
  
  // Agent dispatch
  agentName?: string;
  
  // Sandbox
  sandboxId?: string;
}
```

### Room Configuration

```typescript
// Sent in POST body to /api/token
interface RoomConfigRequest {
  room_config?: {
    agents?: Array<{
      agent_name: string;
      // Optional metadata
      metadata?: Record<string, any>;
    }>;
  };
}
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. **Connection Fails: "Invalid Token"**

**Cause:** API credentials misconfigured or expired

**Solution:**
```bash
# Verify .env.local has correct values
LIVEKIT_API_KEY=your_actual_key
LIVEKIT_API_SECRET=your_actual_secret
LIVEKIT_URL=wss://your-project.livekit.cloud
```

#### 2. **Agent Not Connecting**

**Cause:** Agent name mismatch or agent not running

**Solution:**
```typescript
// Ensure agent name matches deployed agent
const session = useSession(tokenSource, {
  agentName: 'my-agent'  // Must match agent registered on server
});
```

**Check agent is running:**
```bash
# For Python agents
uv run src/agent.py dev

# For Node.js agents
pnpm dev
```

#### 3. **No Audio Output**

**Cause:** Browser audio context not started or audio permissions

**Solution:**
- Use `<StartAudioButton>` component to resume audio context
- Check browser audio permissions
- Verify `<RoomAudioRenderer>` is rendered

```typescript
<AgentSessionProvider session={session}>
  {children}
  {/* Audio renderer is included automatically */}
</AgentSessionProvider>

<StartAudioButton label="Start Audio" />
```

#### 4. **CORS Errors**

**Cause:** Token endpoint not accessible

**Solution:**
For development, ensure Next.js API route is running:
```bash
pnpm dev
```

For production, ensure token endpoint returns proper CORS headers.

#### 5. **Room Configuration Not Applied**

**Cause:** Room config not passed correctly

**Solution:**
```typescript
// Verify room_config structure in token request
const tokenSource = TokenSource.endpoint('/api/token');

// OR for custom token source
TokenSource.custom(async () => {
  const res = await fetch('/api/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      room_config: {
        agents: [{ agent_name: 'my-agent' }]
      }
    })
  });
  return res.json();
});
```

#### 6. **Connection Drops Frequently**

**Cause:** Network issues or token expiration

**Solutions:**
- Increase token TTL in `createParticipantToken`:
  ```typescript
  const at = new AccessToken(API_KEY, API_SECRET, {
    ...userInfo,
    ttl: '1h',  // Increase from default 15m
  });
  ```
- Implement token refresh logic
- Check network stability

### Debug Mode

Enable debug logging:

```typescript
// In components/app/app.tsx
function AppSetup() {
  useDebugMode({ enabled: true });  // Enable in development
  useAgentErrors();  // Display agent errors as toasts
  return null;
}
```

### Logging Connection Events

```typescript
const { room } = useSessionContext();

useEffect(() => {
  if (!room) return;
  
  room.on('connected', () => {
    console.log('Connected to room:', room.name);
  });
  
  room.on('disconnected', (reason) => {
    console.log('Disconnected:', reason);
  });
  
  room.on('reconnecting', () => {
    console.log('Reconnecting...');
  });
  
  room.on('reconnected', () => {
    console.log('Reconnected successfully');
  });
  
  return () => {
    room.removeAllListeners();
  };
}, [room]);
```

---

## Summary

This guide covered the complete LiveKit connection flow:

1. **Architecture:** Three-layer system (App → Session → Token)
2. **Components:** App, ViewController, AgentSessionProvider, TokenSource
3. **Authentication:** JWT token generation with VideoGrant permissions
4. **Connection Flow:** 7-step process from user click to media streaming
5. **Session Management:** State lifecycle and media track handling
6. **Configuration:** Environment variables and app config options
7. **Troubleshooting:** Common issues and debug techniques

### Key Takeaways

- **TokenSource** abstracts token retrieval (endpoint or custom)
- **useSession** hook manages connection lifecycle
- **AgentSessionProvider** provides session context to components
- **JWT tokens** contain identity, permissions, and room config
- **Agent dispatch** is configured via `room_config` in token request
- **Media tracks** are managed via Room API and rendered via RoomAudioRenderer

### Next Steps

- Explore [LiveKit Agents Documentation](https://docs.livekit.io/agents)
- Check out [Agent Examples](https://github.com/livekit-examples)
- Build custom agents with [Agent SDK](https://docs.livekit.io/agents/build)
- Deploy to [LiveKit Cloud](https://cloud.livekit.io)

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-04  
**Repository:** https://github.com/livekit-examples/agent-starter-react
