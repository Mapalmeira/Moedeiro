export interface ExternalAccessGrant {
  grant_uuid: string;
  external_access_uuid: string;
  name: string;
  created_at: number;
}

export interface CreatedExternalAccessGrant extends ExternalAccessGrant {
  token: string;
}

export interface ExternalAccessCredentials {
  current_password: string;
  totp_code?: string | null;
}

export interface CreateExternalAccessRequest extends ExternalAccessCredentials {
  name: string;
}
