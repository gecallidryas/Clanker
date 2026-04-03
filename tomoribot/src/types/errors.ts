/**
 * Custom error indicating the database is temporarily unreachable.
 * Thrown by DB read functions when a query fails due to connection issues,
 * NOT when data is genuinely absent. This allows the cache and UI layers
 * to differentiate "server not set up" from "DB temporarily unavailable"
 * and show the appropriate user-facing message.
 */
export class DatabaseUnavailableError extends Error {
	constructor(message: string) {
		super(message);
		this.name = "DatabaseUnavailableError";
	}
}
