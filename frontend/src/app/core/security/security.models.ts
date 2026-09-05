export type TotpStatus = 'unknown' | 'disabled' | 'enabled';

export interface TotpStatusResponse {
  enabled: boolean;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  totp_code?: string | null;
}

export interface StartTotpSetupRequest {
  current_password: string;
}

export interface StartTotpSetupResponse {
  provisioning_uri: string;
}

export interface ConfirmTotpRequest {
  code: string;
}

export interface DisableTotpRequest {
  current_password: string;
  code: string;
}
