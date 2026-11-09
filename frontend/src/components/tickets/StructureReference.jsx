// Presents stable nested-work identifiers without exposing database row IDs.
import "./StructureReference.css";

function StructureReference({ prefix, referenceNumber, id, ticketPublicId, itemName }) {
  const hasReferenceNumber = referenceNumber !== null && referenceNumber !== undefined;
  const persisted = hasReferenceNumber || (id !== null && id !== undefined);
  // id is retained only for legacy consumers while rollout completes.
  const reference = hasReferenceNumber
    ? `${prefix}-${String(referenceNumber).padStart(3, "0")}`
    : persisted
      ? `${prefix}-${id}`
      : "NEW";
  const completeReference = persisted && ticketPublicId
    ? `${ticketPublicId}-${reference}`
    : reference;
  const accessibleLabel = persisted
    ? `${itemName} reference ${completeReference}`
    : `New ${itemName}; a permanent reference will be assigned after save`;

  return (
    <span
      className={`structure-reference ${persisted ? "" : "pending"}`}
      aria-label={accessibleLabel}
      title={persisted && completeReference !== reference ? `${accessibleLabel}. Full reference: ${completeReference}` : accessibleLabel}
    >
      {reference}
    </span>
  );
}

export default StructureReference;
