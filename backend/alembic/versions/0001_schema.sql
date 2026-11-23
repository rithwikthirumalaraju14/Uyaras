CREATE TABLE audit_log (
	id VARCHAR(32) NOT NULL, 
	actor VARCHAR(32) NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	target VARCHAR(100) NOT NULL, 
	detail JSON NOT NULL, 
	created INTEGER NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE carts (
	id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE categories (
	id VARCHAR(32) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	slug VARCHAR(120) NOT NULL, 
	parent_id VARCHAR(32), 
	published BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (slug), 
	FOREIGN KEY(parent_id) REFERENCES categories (id)
);

CREATE TABLE collections (
	id VARCHAR(32) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	slug VARCHAR(120) NOT NULL, 
	published BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (slug)
);

CREATE TABLE delivery_rules (
	pin VARCHAR(6) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	shipping INTEGER NOT NULL, 
	free_over INTEGER NOT NULL, 
	cod BOOLEAN NOT NULL, 
	cod_fee INTEGER NOT NULL, 
	cod_max INTEGER NOT NULL, 
	days VARCHAR(100) NOT NULL, 
	verified BOOLEAN NOT NULL, 
	PRIMARY KEY (pin)
);

CREATE TABLE promotions (
	code VARCHAR(40) NOT NULL, 
	percent INTEGER NOT NULL, 
	minimum INTEGER NOT NULL, 
	"limit" INTEGER NOT NULL, 
	used INTEGER NOT NULL, 
	active BOOLEAN NOT NULL, 
	start INTEGER NOT NULL, 
	"end" INTEGER NOT NULL, 
	eligible_products JSON NOT NULL, 
	eligible_categories JSON NOT NULL, 
	PRIMARY KEY (code), 
	CHECK (percent >= 0 AND percent <= 100 AND used >= 0)
);

CREATE TABLE rate_limits (
	key VARCHAR(64) NOT NULL, 
	count INTEGER NOT NULL, 
	expires INTEGER NOT NULL, 
	PRIMARY KEY (key)
);

CREATE TABLE settings (
	key VARCHAR(80) NOT NULL, 
	value JSON NOT NULL, 
	PRIMARY KEY (key)
);

CREATE TABLE users (
	id VARCHAR(32) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password TEXT NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

CREATE TABLE webhook_events (
	id VARCHAR(100) NOT NULL, 
	payload_hash VARCHAR(64) NOT NULL, 
	created INTEGER NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE addresses (
	id VARCHAR(32) NOT NULL, 
	user_id VARCHAR(32) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	phone VARCHAR(10) NOT NULL, 
	line VARCHAR(300) NOT NULL, 
	city VARCHAR(100) NOT NULL, 
	state VARCHAR(100) NOT NULL, 
	pin VARCHAR(6) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_addresses_user_id ON addresses (user_id);

CREATE TABLE outbox (
	id VARCHAR(32) NOT NULL, 
	user_id VARCHAR(32) NOT NULL, 
	message TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	attempts INTEGER NOT NULL, 
	available INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE products (
	id VARCHAR(32) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	slug VARCHAR(160) NOT NULL, 
	description TEXT NOT NULL, 
	category_id VARCHAR(32) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	care TEXT NOT NULL, 
	size_guide TEXT NOT NULL, 
	seo_title VARCHAR(160) NOT NULL, 
	seo_description VARCHAR(320) NOT NULL, 
	created INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (slug), 
	FOREIGN KEY(category_id) REFERENCES categories (id)
);

CREATE TABLE quotes (
	id VARCHAR(32) NOT NULL, 
	user_id VARCHAR(32) NOT NULL, 
	cart_version INTEGER NOT NULL, 
	snapshot JSON NOT NULL, 
	expires INTEGER NOT NULL, 
	consumed BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_quotes_user_id ON quotes (user_id);

CREATE TABLE reset_tokens (
	id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(32) NOT NULL, 
	expires INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE sessions (
	id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(32), 
	csrf VARCHAR(64) NOT NULL, 
	expires INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE media (
	id VARCHAR(32) NOT NULL, 
	product_id VARCHAR(32) NOT NULL, 
	url TEXT NOT NULL, 
	alt VARCHAR(200) NOT NULL, 
	object_key VARCHAR(300) NOT NULL, 
	position INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id)
);

CREATE INDEX ix_media_product_id ON media (product_id);

CREATE TABLE orders (
	id VARCHAR(32) NOT NULL, 
	user_id VARCHAR(32) NOT NULL, 
	idempotency_key VARCHAR(100) NOT NULL, 
	quote_id VARCHAR(32) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	payment VARCHAR(30) NOT NULL, 
	method VARCHAR(20) NOT NULL, 
	totals JSON NOT NULL, 
	address JSON NOT NULL, 
	coupon VARCHAR(40) NOT NULL, 
	created INTEGER NOT NULL, 
	expires INTEGER NOT NULL, 
	demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, idempotency_key), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	UNIQUE (quote_id), 
	FOREIGN KEY(quote_id) REFERENCES quotes (id)
);

CREATE INDEX ix_orders_user_id ON orders (user_id);

CREATE TABLE product_collections (
	product_id VARCHAR(32) NOT NULL, 
	collection_id VARCHAR(32) NOT NULL, 
	PRIMARY KEY (product_id, collection_id), 
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE, 
	FOREIGN KEY(collection_id) REFERENCES collections (id) ON DELETE CASCADE
);

CREATE TABLE variants (
	sku VARCHAR(80) NOT NULL, 
	product_id VARCHAR(32) NOT NULL, 
	size VARCHAR(20) NOT NULL, 
	colour VARCHAR(50) NOT NULL, 
	price INTEGER NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (sku), 
	UNIQUE (product_id, size, colour), 
	CHECK (price >= 0), 
	FOREIGN KEY(product_id) REFERENCES products (id)
);

CREATE INDEX ix_variants_product_id ON variants (product_id);

CREATE TABLE cart_items (
	cart_id VARCHAR(64) NOT NULL, 
	sku VARCHAR(80) NOT NULL, 
	quantity INTEGER NOT NULL, 
	PRIMARY KEY (cart_id, sku), 
	CHECK (quantity > 0 AND quantity <= 20), 
	FOREIGN KEY(cart_id) REFERENCES carts (id) ON DELETE CASCADE, 
	FOREIGN KEY(sku) REFERENCES variants (sku)
);

CREATE TABLE cod_ledger (
	order_id VARCHAR(32) NOT NULL, 
	due INTEGER NOT NULL, 
	collected INTEGER NOT NULL, 
	remitted INTEGER NOT NULL, 
	reference VARCHAR(100) NOT NULL, 
	PRIMARY KEY (order_id), 
	CHECK (due >= collected AND collected >= remitted AND remitted >= 0), 
	FOREIGN KEY(order_id) REFERENCES orders (id)
);

CREATE TABLE inventory (
	sku VARCHAR(80) NOT NULL, 
	on_hand INTEGER NOT NULL, 
	reserved INTEGER NOT NULL, 
	low_stock INTEGER NOT NULL, 
	real_stock BOOLEAN NOT NULL, 
	location VARCHAR(80) NOT NULL, 
	PRIMARY KEY (sku), 
	CHECK (on_hand >= 0 AND reserved >= 0 AND reserved <= on_hand), 
	FOREIGN KEY(sku) REFERENCES variants (sku)
);

CREATE TABLE inventory_movements (
	id VARCHAR(32) NOT NULL, 
	sku VARCHAR(80) NOT NULL, 
	delta INTEGER NOT NULL, 
	reason VARCHAR(200) NOT NULL, 
	actor VARCHAR(32) NOT NULL, 
	created INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sku) REFERENCES variants (sku)
);

CREATE INDEX ix_inventory_movements_sku ON inventory_movements (sku);

CREATE TABLE order_events (
	id VARCHAR(32) NOT NULL, 
	order_id VARCHAR(32) NOT NULL, 
	message VARCHAR(300) NOT NULL, 
	created INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id)
);

CREATE INDEX ix_order_events_order_id ON order_events (order_id);

CREATE TABLE order_items (
	id VARCHAR(32) NOT NULL, 
	order_id VARCHAR(32) NOT NULL, 
	sku VARCHAR(80) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	size VARCHAR(20) NOT NULL, 
	colour VARCHAR(50) NOT NULL, 
	price INTEGER NOT NULL, 
	quantity INTEGER NOT NULL, 
	discount INTEGER NOT NULL, 
	included_tax INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	FOREIGN KEY(sku) REFERENCES variants (sku)
);

CREATE INDEX ix_order_items_order_id ON order_items (order_id);

CREATE TABLE payment_attempts (
	id VARCHAR(32) NOT NULL, 
	order_id VARCHAR(32) NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	amount INTEGER NOT NULL, 
	reference VARCHAR(100) NOT NULL, 
	created INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id)
);

CREATE INDEX ix_payment_attempts_order_id ON payment_attempts (order_id);

CREATE TABLE shipments (
	order_id VARCHAR(32) NOT NULL, 
	carrier VARCHAR(80) NOT NULL, 
	tracking VARCHAR(100) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	delivered INTEGER NOT NULL, 
	PRIMARY KEY (order_id), 
	FOREIGN KEY(order_id) REFERENCES orders (id)
);

CREATE TABLE refunds (
	id VARCHAR(32) NOT NULL, 
	order_id VARCHAR(32) NOT NULL, 
	amount INTEGER NOT NULL, 
	reference VARCHAR(100) NOT NULL, 
	reason VARCHAR(300) NOT NULL, 
	payment_attempt_id VARCHAR(32), 
	created INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (amount > 0), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	UNIQUE (reference), 
	FOREIGN KEY(payment_attempt_id) REFERENCES payment_attempts (id)
);

CREATE INDEX ix_refunds_order_id ON refunds (order_id);

CREATE TABLE reservations (
	order_id VARCHAR(32) NOT NULL, 
	sku VARCHAR(80) NOT NULL, 
	quantity INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	PRIMARY KEY (order_id, sku), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	FOREIGN KEY(sku) REFERENCES inventory (sku)
);

CREATE TABLE return_requests (
	id VARCHAR(32) NOT NULL, 
	order_id VARCHAR(32) NOT NULL, 
	item_id VARCHAR(32) NOT NULL, 
	quantity INTEGER NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	restocked BOOLEAN NOT NULL, 
	condition VARCHAR(300) NOT NULL, 
	resolution_reference VARCHAR(100) NOT NULL, 
	created INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	FOREIGN KEY(item_id) REFERENCES order_items (id)
);

CREATE INDEX ix_return_requests_order_id ON return_requests (order_id);