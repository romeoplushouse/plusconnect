CREATE TABLE IF NOT EXISTS hotel_state (
    hotel_id VARCHAR(128) PRIMARY KEY,
    last_synced_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reservations_state (
    hotel_id VARCHAR(128) NOT NULL,
    reservation_id VARCHAR(128) NOT NULL,
    hash CHAR(64) NOT NULL,
    loxone_uuid VARCHAR(128) NULL,
    last_status VARCHAR(64) NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (hotel_id, reservation_id)
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hotel_id VARCHAR(128) NOT NULL,
    started_at DATETIME NOT NULL,
    finished_at DATETIME NULL,
    status VARCHAR(32) NOT NULL,
    processed INT DEFAULT 0,
    changed INT DEFAULT 0,
    errors_count INT DEFAULT 0,
    message TEXT
);

CREATE TABLE IF NOT EXISTS sync_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hotel_id VARCHAR(128) NOT NULL,
    timestamp DATETIME NOT NULL,
    level VARCHAR(16) NOT NULL,
    source VARCHAR(32) NOT NULL,
    code VARCHAR(32) NULL,
    reservation_id VARCHAR(128) NULL,
    message TEXT
);

CREATE TABLE IF NOT EXISTS service_health (
    hotel_id VARCHAR(128) NOT NULL,
    loxone_status VARCHAR(16) NOT NULL,
    previo_xml_status VARCHAR(16) NOT NULL,
    previo_rest_status VARCHAR(16) NOT NULL,
    loxone_latency_ms INT NULL,
    previo_xml_latency_ms INT NULL,
    previo_rest_latency_ms INT NULL,
    checked_at DATETIME NOT NULL,
    PRIMARY KEY (hotel_id, checked_at)
);
