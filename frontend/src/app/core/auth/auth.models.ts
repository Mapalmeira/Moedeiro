export interface AuthenticationSession {
  name: string;
}

export interface LoginRequest {
  name: string;
  password: string;
  remember: boolean;
  totp_code?: string | null;
}

export interface PasswordRecoveryRequest {
  name: string;
  recovery_code: string;
  new_password: string;
  totp_code?: string | null;
}

export interface RegistrationRequest {
  invitation_code: string;
  name: string;
  password: string;
}
