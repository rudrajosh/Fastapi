u# FastAPI Social Media API

This is a FastAPI-based social media API with user authentication, posts, likes, and comments functionality.

## Features

- User registration and login with JWT authentication
- Create, read, update, delete (CRUD) posts
- Like and unlike posts
- Create, read, update, delete comments on posts
- List posts with likes count
- Secure routes with token-based authentication

## Setup

1. Clone the repository.

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary passlib[bcrypt] python-jose python-dotenv
```

4. Set environment variables in a `.env` file or your environment:

```
DATABASE_URL=postgresql://postgres:1234@localhost/socialmedia
SECRET_KEY=your_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

5. Run the FastAPI server:

```bash
uvicorn app:app --reload
```

## API Usage with Postman

### 1. Register a user

- Method: POST
- URL: `http://localhost:8000/register`
- Body (JSON):

```json
{
  "username": "yourusername",
  "email": "youremail@example.com",
  "password": "yourpassword"
}
```

### 2. Login to get access token

- Method: POST
- URL: `http://localhost:8000/login`
- Body (x-www-form-urlencoded):

```
username=yourusername
password=yourpassword
```

- Response contains `access_token`

### 3. Use the access token in Authorization header for authenticated requests

- Header key: `Authorization`
- Header value: `Bearer <access_token>`

### 4. Create a post

- Method: POST
- URL: `http://localhost:8000/posts/`
- Body (JSON):

```json
{
  "title": "Post Title",
  "content": "Post content"
}
```

### 5. Like a post

- Method: POST
- URL: `http://localhost:8000/posts/{post_id}/likes`

### 6. Unlike a post

- Method: DELETE
- URL: `http://localhost:8000/posts/{post_id}/likes`

### 7. List posts

- Method: GET
- URL: `http://localhost:8000/posts/`

### 8. List posts with likes count

- Method: GET
- URL: `http://localhost:8000/posts/with_likes`

### 9. Create a comment

- Method: POST
- URL: `http://localhost:8000/comments/`
- Body (JSON):

```json
{
  "content": "Comment text",
  "post_id": 1
}
```

### 10. List comments

- Method: GET
- URL: `http://localhost:8000/comments/`

### 11. Get a specific comment

- Method: GET
- URL: `http://localhost:8000/comments/{comment_id}`

### 12. Update a comment (only by owner)

- Method: PUT
- URL: `http://localhost:8000/comments/{comment_id}`
- Body (JSON):

```json
{
  "content": "Updated comment text",
  "post_id": 1
}
```

### 13. Delete a comment (only by owner)

- Method: DELETE
- URL: `http://localhost:8000/comments/{comment_id}`


