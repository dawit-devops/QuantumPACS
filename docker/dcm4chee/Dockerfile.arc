FROM dcm4che/dcm4chee-arc-psql:5.35.0

# weasis-pacs-connector 8.0.0 — vendored (see scripts/fetch_weasis.sh for the
# pinned SHA-256). The dcm4chee arc entrypoint deploys wars from
# /docker-entrypoint.d/deployments/ and copies property files from
# /docker-entrypoint.d/configuration/ into the WildFly configuration dir at
# container start.
COPY weasis-pacs-connector.war /docker-entrypoint.d/deployments/
COPY weasis-pacs-connector.properties /docker-entrypoint.d/configuration/
COPY dicom-dcm4chee-arc.properties /docker-entrypoint.d/configuration/

# The archive must be able to reach the QuantumPACS feed SCP (AE QUANTUMPACS)
# for Option-B export (dcm4chee C-STORE -> QuantumPACS 11113). In compose the
# host is reachable as the Docker bridge gateway; the AE entry itself lives in
# LDAP (configured in Phase 1 gates / dcm4chee UI).
EXPOSE 8080 8443 9990 9993 11112 2762 2575 12575
