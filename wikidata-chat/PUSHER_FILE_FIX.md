# Pusher File Size Fix

## Problem
The visualization files (JSON, Mermaid, TTL) were being sent through Pusher WebSocket messages, but Pusher has size limitations that caused these large files to fail transmission.

## Solution
Changed the system to serve visualization files via HTTP download URLs instead of sending file contents through Pusher.

## Changes Made

### Backend Changes

#### 1. `backend/agent/agent.py`
- Modified `query()` method to return file paths instead of file contents
- Removed code that reads file contents into memory
- Now returns `self.visualization_files` (paths) instead of `visualization_files_content`

#### 2. `backend/chat/views.py`
- Added new `download_visualization()` action to serve files for download
- Modified `send_message()` to create download URLs instead of file contents
- Added proper imports for file handling

#### 3. `backend/chat/consumers.py`
- Updated WebSocket consumer to create download URLs instead of file contents
- Removed obsolete `handle_file_request()` method
- Added proper imports

#### 4. `backend/chat/urls.py`
- Added new URL pattern for file downloads: `/chats/<uuid:pk>/download_visualization/`

### Frontend Changes

#### 1. `frontend/src/components/VisualizationFiles.jsx`
- Updated to use download URLs instead of creating blobs from content
- Downloads now use direct HTTP requests to the backend
- Added proper API URL construction

#### 2. `frontend/src/types/index.ts`
- Updated `VisualizationFile` interface to use `download_url` instead of `content`

## New File Structure

### Before (via Pusher):
```json
{
  "visualization_files": {
    "json": {
      "content": "... large file content ...",
      "file_name": "filename.json"
    }
  }
}
```

### After (via URLs):
```json
{
  "visualization_files": {
    "json": {
      "download_url": "/api/chats/uuid/download_visualization/?type=json",
      "file_name": "filename.json"
    }
  }
}
```

## API Endpoints

### New Download Endpoint
- **URL**: `GET /api/chats/{chat_id}/download_visualization/?type={file_type}`
- **Parameters**: 
  - `chat_id`: UUID of the chat
  - `type`: File type (`json`, `mermaid`, or `ttl`)
- **Response**: File download with appropriate Content-Type and Content-Disposition headers

## Benefits

1. **No Size Limits**: Files are served via HTTP, not constrained by Pusher message size limits
2. **Better Performance**: Only small URLs are sent through Pusher instead of large file contents
3. **Proper Downloads**: Files are served with correct MIME types and download headers
4. **Scalability**: Large files don't impact real-time messaging performance

## Testing

1. Start the backend server
2. Send a message that generates visualization files
3. Verify that download buttons appear in the frontend
4. Click download buttons to verify files download correctly
5. Check that Pusher messages are now small and contain only URLs

The system now efficiently handles large visualization files without overwhelming the real-time messaging system.
