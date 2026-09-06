export type TotpStatus = 'unknown' | 'ENABLED' | 'DISABLED' | 'PENDING';

export interface TotpResponse {
  state: Exclude<TotpStatus, 'unknown'>;
  provisioning_uri: string | null;
  expires_at: number | null;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  totp_code?: string | null;
}

export interface StartTotpSetupRequest {
  current_password: string;
}

export interface ConfirmTotpRequest {
  code: string;
}

export interface DisableTotpRequest {
  current_password: string;
  code: string;
}
