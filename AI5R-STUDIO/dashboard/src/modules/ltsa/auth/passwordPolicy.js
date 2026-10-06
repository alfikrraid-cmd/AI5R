// LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- client-side mirror of
// CORE-SERVICES/API/auth_password.py validate_password_policy(), so a form can
// explain a rejection before submitting. The backend remains the enforcement
// point; this never decides on its own that a password is acceptable.
export const PASSWORD_MIN_LENGTH = 12;
export const PASSWORD_MAX_LENGTH = 128;

export const PASSWORD_POLICY_HINT = `Use ${PASSWORD_MIN_LENGTH}–${PASSWORD_MAX_LENGTH} characters, different from your username and email.`;

// Returns a user-facing message, or null when the password passes the policy.
export function passwordPolicyError(password, { username, email } = {}) {
  if (!password || !password.trim()) return "Please enter a new password.";
  if (password.length < PASSWORD_MIN_LENGTH) return `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`;
  if (password.length > PASSWORD_MAX_LENGTH) return `Password must be at most ${PASSWORD_MAX_LENGTH} characters.`;
  const candidate = password.trim().toLowerCase();
  if (username && candidate === username.trim().toLowerCase()) return "Password must not be the same as your username.";
  if (email && candidate === email.trim().toLowerCase()) return "Password must not be the same as your email address.";
  return null;
}
