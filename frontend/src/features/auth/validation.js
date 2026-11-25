// The same rules as the backend (security/passwords.py), checked before sending so the error shows under its field
export const PASSWORD_MIN_LENGTH = 10;
export const PASSWORD_MAX_LENGTH = 128;
export const NAME_MAX_LENGTH = 100;

// Something before and after the @ and a dot in the domain: enough to catch a typo, the backend checks the rest
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Whether the email is worth sending: with the spaces around it trimmed, as it's sent
export function isEmail(value) {
  return EMAIL.test(value.trim());
}
