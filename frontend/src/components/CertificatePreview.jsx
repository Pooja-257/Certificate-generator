const formatDate = (iso) =>
  iso ? new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" }) : "Issue date";

// A scaled-down mock of the PDF. Sizes use cqw (container width units) so it scales with its box.
export default function CertificatePreview({ values, recipient }) {
  return (
    <figure className="cert-wrap">
      <div className="cert">
        <div className="cert-inner">
          <p className="cert-org">{values.organization_name || "Organization name"}</p>
          <h3 className="cert-title">{values.certificate_title || "Certificate title"}</h3>
          <span className="cert-divider" />
          <p className="cert-small">This certificate is proudly presented to</p>
          <p className="cert-name">{recipient?.name || "Recipient name"}</p>
          <p className="cert-small">for successfully participating in</p>
          <p className="cert-course">{recipient?.course || "Course"}</p>
          <p className="cert-small">
            as part of {values.event_name || "the event"}, organized by {values.organization_name || "the organization"}.
          </p>
          <div className="cert-foot">
            <span>{formatDate(values.issue_date)}</span>
            <span className="cert-seal">C</span>
            <span>CERT-0001-00001</span>
          </div>
        </div>
      </div>
      <figcaption>Preview of the PDF each recipient receives</figcaption>
    </figure>
  );
}
