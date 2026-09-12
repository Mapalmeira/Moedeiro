ALTER TABLE financial_movement
ADD COLUMN special_type TEXT CHECK (special_type IS NULL OR special_type IN ('FEE'));

UPDATE financial_movement AS fee
SET special_type = 'FEE'
WHERE fee.value < 0
  AND EXISTS (
      SELECT 1
      FROM financial_event AS event
      WHERE event.uuid = fee.financial_event_uuid
        AND event.type = 'ACCOUNT_TRANSFER'
  )
  AND EXISTS (
      SELECT 1
      FROM financial_movement AS destination
      WHERE destination.financial_event_uuid = fee.financial_event_uuid
        AND destination.value > 0
        AND destination.account_uuid = fee.account_uuid
  );
