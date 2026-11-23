CREATE TABLE category (
    id VARCHAR(36) PRIMARY KEY,
    parent_id VARCHAR(36) REFERENCES category(id),
    slug VARCHAR(160) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (parent_id IS NULL OR parent_id <> id)
);
CREATE INDEX category_parent_idx ON category(parent_id);
CREATE TABLE product (
    id VARCHAR(36) PRIMARY KEY,
    slug VARCHAR(160) NOT NULL UNIQUE,
    name VARCHAR(180) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status VARCHAR(16) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published','archived'))
);
CREATE TABLE product_category (
    product_id VARCHAR(36) NOT NULL REFERENCES product(id),
    category_id VARCHAR(36) NOT NULL REFERENCES category(id),
    PRIMARY KEY (product_id, category_id)
);
CREATE TABLE variant (
    id VARCHAR(36) PRIMARY KEY,
    product_id VARCHAR(36) NOT NULL REFERENCES product(id),
    sku VARCHAR(64) NOT NULL UNIQUE,
    size_label VARCHAR(64) NOT NULL,
    colour_label VARCHAR(64) NOT NULL,
    unit_price_paise BIGINT NOT NULL CHECK (unit_price_paise >= 0),
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (product_id, size_label, colour_label)
);
CREATE TABLE inventory_location (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL
);
CREATE TABLE inventory_balance (
    variant_id VARCHAR(36) NOT NULL REFERENCES variant(id),
    location_id VARCHAR(36) NOT NULL REFERENCES inventory_location(id),
    on_hand INTEGER NOT NULL DEFAULT 0 CHECK (on_hand >= 0),
    reserved INTEGER NOT NULL DEFAULT 0 CHECK (reserved >= 0 AND reserved <= on_hand),
    PRIMARY KEY (variant_id, location_id)
);
