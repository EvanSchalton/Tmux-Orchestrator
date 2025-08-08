# Example Feature Request Template

## Feature Request: User Authentication System

We need to implement a comprehensive user authentication system for our web application. The system should support standard email/password authentication with secure password storage, session management, and basic account recovery features. Users should be able to register, log in, log out, and reset their passwords through a forgot password flow.

The authentication should integrate seamlessly with our existing Next.js frontend and FastAPI backend, maintaining our current design system for all UI components. Security is paramount - we need proper password hashing, CSRF protection, and secure session handling. The system should also lay the groundwork for future OAuth integration, though that's not needed in this initial implementation.

Key Requirements:
- Email/password registration and login
- Secure password storage with bcrypt
- JWT-based session management
- Password reset via email
- Account activation via email
- Rate limiting on auth endpoints
- Comprehensive error handling

Technical Considerations:
- Use existing Postgres database
- Integrate with current email service
- Follow REST API conventions
- Maintain existing UI/UX patterns
- Add comprehensive test coverage
- Document all API endpoints