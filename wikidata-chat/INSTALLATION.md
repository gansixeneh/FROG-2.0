# Installation Instructions

## Backend Dependencies

You mentioned Pusher is already installed, but if you need to install it:

```bash
cd backend
pip install pusher
```

## Frontend Dependencies  

You mentioned Pusher is already installed, but if you need to install it:

```bash
cd frontend
npm install pusher-js
```

## Environment Variables

The Pusher credentials are now hardcoded in the settings, but for production you should use environment variables:

### Backend (.env file):
```
PUSHER_APP_ID=1998736
PUSHER_KEY=0379edb726d89ea8c1e9
PUSHER_SECRET=f463c5ed7feecb491a7c
PUSHER_CLUSTER=ap1
```

### Frontend (.env.local file):
```
REACT_APP_PUSHER_KEY=0379edb726d89ea8c1e9
REACT_APP_PUSHER_CLUSTER=ap1
```

## Testing the Migration

1. Start the backend:
```bash
cd backend
python manage.py runserver
```

2. Start the frontend:
```bash
cd frontend
npm start
```

3. Open the application and test:
   - Create a new chat
   - Send a message
   - Verify real-time debug messages appear
   - Verify response is received

## Key Changes Summary

✅ WebSocket connections replaced with Pusher
✅ Real-time functionality preserved
✅ Debug messages still appear in real-time
✅ Same user experience maintained
✅ No 1-minute timeout limitations
