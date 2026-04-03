import {
  GetSecretValueCommand,
  SecretsManagerClient,
} from "@aws-sdk/client-secrets-manager";
import { log } from "@/utils/misc/logger";

/**
 * Interface defining all secrets required for TomoriBot production deployment.
 *
 * Core Secrets:
 * - Discord bot authentication token
 * - PostgreSQL database connection parameters
 * - Encryption key for database-stored API keys
 *
 * Optional Secrets:
 * - CRYPTO_SECRET_V1, V2, etc. for key rotation support
 * - DISCORD_WEBHOOK_URL for logging webhooks
 */
export interface TomoriSecrets {
  DISCORD_TOKEN: string;
  POSTGRES_HOST: string;
  POSTGRES_PORT: string;
  POSTGRES_USER: string;
  POSTGRES_PASSWORD: string;
  POSTGRES_DB: string;
  CRYPTO_SECRET: string;
  CRYPTO_SECRET_V1?: string; // Optional: Key rotation support
  CRYPTO_SECRET_V2?: string; // Optional: Key rotation support
  CRYPTO_SECRET_V3?: string; // Optional: Key rotation support
  DISCORD_WEBHOOK_URL?: string; // Optional: Error logging webhook
  AVATAR_S3_BUCKET?: string;
  AVATAR_S3_REGION?: string;
  AVATAR_S3_PREFIX?: string;
  AVATAR_PUBLIC_BASE_URL?: string;
  CHARREF_S3_BUCKET?: string;
  CHARREF_S3_REGION?: string;
  CHARREF_S3_PREFIX?: string;
  CHARREF_PUBLIC_BASE_URL?: string;
  // Matrix Appservice Bridge (optional — leave unset to disable the bridge entirely)
  MATRIX_HOMESERVER_URL?: string; // e.g., http://localhost:8448 or https://your-hs.example.com
  MATRIX_ACCESS_TOKEN?: string; // Appservice token (as_token) used to authenticate to the homeserver
  MATRIX_BOT_USER_ID?: string; // e.g., @tomoribot:yourdomain.com
  MATRIX_SERVER_NAME?: string; // Homeserver domain (e.g., localhost or yourdomain.com)
  MATRIX_HS_TOKEN?: string; // Homeserver token (hs_token) — homeserver sends this to verify its identity
  MATRIX_APPSERVICE_PUBLIC_URL?: string; // Optional callback URL used in appservice registration for remote homeservers
  TOPGG_TOKEN?: string; // Optional: Top.gg API token for posting server stats
  [key: string]: string | undefined; // Allow dynamic CRYPTO_SECRET_V* keys
}

/**
 * Fetches application secrets from AWS Secrets Manager (production) or process.env (development).
 *
 * Environment-Based Behavior:
 * - Development (RUN_ENV !== 'production' OR RUN_ENV not set):
 *   - Reads secrets from process.env (loaded via dotenv)
 *   - No AWS API calls
 *   - Safe default for local users without AWS setup
 *
 * - Production (RUN_ENV === 'production'):
 *   - Fetches from AWS Secrets Manager
 *   - Region: Configurable via AWS_REGION (defaults to us-east-1)
 *   - Secret name: "tomoribot/production"
 *   - Parses JSON string and validates required fields
 *   - Auto-detects CRYPTO_SECRET_V* key versions
 *
 * AWS Configuration:
 * - AWS_REGION environment variable (defaults to "us-east-1")
 * - AWS credentials from environment, IAM role, or ~/.aws/credentials
 *
 * Key Version Auto-Detection:
 * - Scans for CRYPTO_SECRET_V1, CRYPTO_SECRET_V2, CRYPTO_SECRET_V3, etc.
 * - Dynamically includes all found versions
 * - Integrates seamlessly with existing CryptoKeyManager
 *
 * Error Handling:
 * - Missing required fields → throws error with missing key list
 * - AWS network/permission errors → descriptive error message
 * - Invalid JSON → parse error with guidance
 *
 * @returns {Promise<TomoriSecrets>} Object containing all application secrets
 * @throws {Error} If required secrets are missing or AWS fetch fails
 *
 * @example
 * // In src/index.ts
 * const secrets = await getAppSecrets();
 * process.env.DISCORD_TOKEN = secrets.DISCORD_TOKEN;
 * process.env.POSTGRES_HOST = secrets.POSTGRES_HOST;
 */
export async function getAppSecrets(): Promise<TomoriSecrets> {
  // Default to 'development' if RUN_ENV is not set (safe for local users)
  const runEnv = process.env.RUN_ENV || "development";
  const isProduction = runEnv === "production";
  const isTestProduction = process.env.TEST_PRODUCTION === "true";

  // Development mode OR test production mode: Use process.env (loaded via dotenv)
  // TEST_PRODUCTION allows testing production behavior locally without AWS
  if (!isProduction || isTestProduction) {
    log.info(
      `Loading secrets from .env (${isTestProduction ? "test production" : "development"} mode)`,
    );

    const secrets: TomoriSecrets = {
      DISCORD_TOKEN: process.env.DISCORD_TOKEN || "",
      POSTGRES_HOST: process.env.POSTGRES_HOST || "",
      POSTGRES_PORT: process.env.POSTGRES_PORT || "",
      POSTGRES_USER: process.env.POSTGRES_USER || "",
      POSTGRES_PASSWORD: process.env.POSTGRES_PASSWORD || "",
      POSTGRES_DB: process.env.POSTGRES_DB || "",
      CRYPTO_SECRET: process.env.CRYPTO_SECRET || "",
    };

    // Auto-detect key versions (CRYPTO_SECRET_V1, V2, V3, etc.)
    if (process.env.CRYPTO_SECRET_V1) {
      secrets.CRYPTO_SECRET_V1 = process.env.CRYPTO_SECRET_V1;
    }
    if (process.env.CRYPTO_SECRET_V2) {
      secrets.CRYPTO_SECRET_V2 = process.env.CRYPTO_SECRET_V2;
    }
    if (process.env.CRYPTO_SECRET_V3) {
      secrets.CRYPTO_SECRET_V3 = process.env.CRYPTO_SECRET_V3;
    }

    // Optional webhook URL
    if (process.env.DISCORD_WEBHOOK_URL) {
      secrets.DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;
    }

    if (process.env.AVATAR_S3_BUCKET) {
      secrets.AVATAR_S3_BUCKET = process.env.AVATAR_S3_BUCKET;
    }
    if (process.env.AVATAR_S3_REGION) {
      secrets.AVATAR_S3_REGION = process.env.AVATAR_S3_REGION;
    }
    if (process.env.AVATAR_S3_PREFIX) {
      secrets.AVATAR_S3_PREFIX = process.env.AVATAR_S3_PREFIX;
    }
    if (process.env.AVATAR_PUBLIC_BASE_URL) {
      secrets.AVATAR_PUBLIC_BASE_URL = process.env.AVATAR_PUBLIC_BASE_URL;
    }
    if (process.env.CHARREF_S3_BUCKET) {
      secrets.CHARREF_S3_BUCKET = process.env.CHARREF_S3_BUCKET;
    }
    if (process.env.CHARREF_S3_REGION) {
      secrets.CHARREF_S3_REGION = process.env.CHARREF_S3_REGION;
    }
    if (process.env.CHARREF_S3_PREFIX) {
      secrets.CHARREF_S3_PREFIX = process.env.CHARREF_S3_PREFIX;
    }
    if (process.env.CHARREF_PUBLIC_BASE_URL) {
      secrets.CHARREF_PUBLIC_BASE_URL = process.env.CHARREF_PUBLIC_BASE_URL;
    }

    // Optional Matrix Appservice Bridge credentials
    if (process.env.MATRIX_HOMESERVER_URL) {
      secrets.MATRIX_HOMESERVER_URL = process.env.MATRIX_HOMESERVER_URL;
    }
    if (process.env.MATRIX_ACCESS_TOKEN) {
      secrets.MATRIX_ACCESS_TOKEN = process.env.MATRIX_ACCESS_TOKEN;
    }
    if (process.env.MATRIX_BOT_USER_ID) {
      secrets.MATRIX_BOT_USER_ID = process.env.MATRIX_BOT_USER_ID;
    }
    if (process.env.MATRIX_SERVER_NAME) {
      secrets.MATRIX_SERVER_NAME = process.env.MATRIX_SERVER_NAME;
    }
    if (process.env.MATRIX_HS_TOKEN) {
      secrets.MATRIX_HS_TOKEN = process.env.MATRIX_HS_TOKEN;
    }
    if (process.env.MATRIX_APPSERVICE_PUBLIC_URL) {
      secrets.MATRIX_APPSERVICE_PUBLIC_URL =
        process.env.MATRIX_APPSERVICE_PUBLIC_URL;
    }

    // Optional Top.gg integration token
    if (process.env.TOPGG_TOKEN) {
      secrets.TOPGG_TOKEN = process.env.TOPGG_TOKEN;
    }

    // Validate required fields
    validateRequiredSecrets(secrets);

    return secrets;
  }

  // Production mode: Fetch from AWS Secrets Manager
  const awsRegion = process.env.AWS_REGION || "us-east-1";
  log.info(
    `Fetching secrets from AWS Secrets Manager (production mode, region: ${awsRegion})`,
  );

  try {
    // 1. Create AWS Secrets Manager client with configurable region
    const client = new SecretsManagerClient({ region: awsRegion });

    // 2. Fetch secret value
    const command = new GetSecretValueCommand({
      SecretId: "tomoribot/production",
    });

    const response = await client.send(command);

    // 3. Parse SecretString as JSON
    if (!response.SecretString) {
      throw new Error(
        "AWS Secrets Manager returned empty SecretString. Ensure the secret contains a JSON object.",
      );
    }

    const rawSecrets = JSON.parse(response.SecretString);

    // 4. Build TomoriSecrets object
    const secrets: TomoriSecrets = {
      DISCORD_TOKEN: rawSecrets.DISCORD_TOKEN,
      POSTGRES_HOST: rawSecrets.POSTGRES_HOST,
      POSTGRES_PORT: rawSecrets.POSTGRES_PORT,
      POSTGRES_USER: rawSecrets.POSTGRES_USER,
      POSTGRES_PASSWORD: rawSecrets.POSTGRES_PASSWORD,
      POSTGRES_DB: rawSecrets.POSTGRES_DB,
      CRYPTO_SECRET: rawSecrets.CRYPTO_SECRET,
    };

    // 5. Auto-detect key versions (CRYPTO_SECRET_V1, V2, V3, etc.)
    // This allows for unlimited key rotation versions
    for (const key of Object.keys(rawSecrets)) {
      if (key.startsWith("CRYPTO_SECRET_V")) {
        secrets[key] = rawSecrets[key];
        log.info(`Detected key version: ${key}`);
      }
    }

    // 6. Optional webhook URL
    if (rawSecrets.DISCORD_WEBHOOK_URL) {
      secrets.DISCORD_WEBHOOK_URL = rawSecrets.DISCORD_WEBHOOK_URL;
    }

    if (rawSecrets.AVATAR_S3_BUCKET) {
      secrets.AVATAR_S3_BUCKET = rawSecrets.AVATAR_S3_BUCKET;
    }
    if (rawSecrets.AVATAR_S3_REGION) {
      secrets.AVATAR_S3_REGION = rawSecrets.AVATAR_S3_REGION;
    }
    if (rawSecrets.AVATAR_S3_PREFIX) {
      secrets.AVATAR_S3_PREFIX = rawSecrets.AVATAR_S3_PREFIX;
    }
    if (rawSecrets.AVATAR_PUBLIC_BASE_URL) {
      secrets.AVATAR_PUBLIC_BASE_URL = rawSecrets.AVATAR_PUBLIC_BASE_URL;
    }
    if (rawSecrets.CHARREF_S3_BUCKET) {
      secrets.CHARREF_S3_BUCKET = rawSecrets.CHARREF_S3_BUCKET;
    }
    if (rawSecrets.CHARREF_S3_REGION) {
      secrets.CHARREF_S3_REGION = rawSecrets.CHARREF_S3_REGION;
    }
    if (rawSecrets.CHARREF_S3_PREFIX) {
      secrets.CHARREF_S3_PREFIX = rawSecrets.CHARREF_S3_PREFIX;
    }
    if (rawSecrets.CHARREF_PUBLIC_BASE_URL) {
      secrets.CHARREF_PUBLIC_BASE_URL = rawSecrets.CHARREF_PUBLIC_BASE_URL;
    }

    // Optional Matrix Appservice Bridge credentials
    if (rawSecrets.MATRIX_HOMESERVER_URL) {
      secrets.MATRIX_HOMESERVER_URL = rawSecrets.MATRIX_HOMESERVER_URL;
    }
    if (rawSecrets.MATRIX_ACCESS_TOKEN) {
      secrets.MATRIX_ACCESS_TOKEN = rawSecrets.MATRIX_ACCESS_TOKEN;
    }
    if (rawSecrets.MATRIX_BOT_USER_ID) {
      secrets.MATRIX_BOT_USER_ID = rawSecrets.MATRIX_BOT_USER_ID;
    }
    if (rawSecrets.MATRIX_SERVER_NAME) {
      secrets.MATRIX_SERVER_NAME = rawSecrets.MATRIX_SERVER_NAME;
    }
    if (rawSecrets.MATRIX_HS_TOKEN) {
      secrets.MATRIX_HS_TOKEN = rawSecrets.MATRIX_HS_TOKEN;
    }
    if (rawSecrets.MATRIX_APPSERVICE_PUBLIC_URL) {
      secrets.MATRIX_APPSERVICE_PUBLIC_URL =
        rawSecrets.MATRIX_APPSERVICE_PUBLIC_URL;
    }

    // Optional Top.gg integration token
    if (rawSecrets.TOPGG_TOKEN) {
      secrets.TOPGG_TOKEN = rawSecrets.TOPGG_TOKEN;
    }

    // 7. Validate required fields
    validateRequiredSecrets(secrets);

    log.info("Successfully loaded secrets from AWS Secrets Manager");

    return secrets;
  } catch (error) {
    // Enhance error message for common AWS errors
    if (error instanceof Error) {
      if (error.name === "ResourceNotFoundException") {
        throw new Error(
          `AWS Secrets Manager: Secret "tomoribot/production" not found in ${awsRegion}. ` +
            `Please create the secret in AWS Secrets Manager console.`,
        );
      }

      if (error.name === "AccessDeniedException") {
        throw new Error(
          `AWS Secrets Manager: Access denied to "tomoribot/production". ` +
            `Ensure your IAM user/role has secretsmanager:GetSecretValue permission.`,
        );
      }

      if (error.message.includes("getaddrinfo ENOTFOUND")) {
        throw new Error(
          `AWS Secrets Manager: Network error. ` +
            `Ensure your system has internet connectivity and can reach AWS services.`,
        );
      }
    }

    // Re-throw with context
    log.error(
      "Failed to fetch secrets from AWS Secrets Manager",
      error instanceof Error ? error : new Error(String(error)),
    );

    throw error;
  }
}

/**
 * Validates that all required secrets are present and non-empty.
 *
 * Required Fields:
 * - DISCORD_TOKEN (Discord bot authentication)
 * - POSTGRES_HOST (Database connection)
 * - POSTGRES_PORT (Database port)
 * - POSTGRES_USER (Database user)
 * - POSTGRES_PASSWORD (Database password)
 * - POSTGRES_DB (Database name)
 * - CRYPTO_SECRET (Encryption key for database-stored API keys)
 *
 * @param {TomoriSecrets} secrets - Secrets object to validate
 * @throws {Error} If any required secret is missing or empty
 */
function validateRequiredSecrets(secrets: TomoriSecrets): void {
  const requiredFields: (keyof TomoriSecrets)[] = [
    "DISCORD_TOKEN",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "CRYPTO_SECRET",
  ];

  const missingFields = requiredFields.filter(
    (field) => !secrets[field] || secrets[field] === "",
  );

  if (missingFields.length > 0) {
    throw new Error(
      `Missing required secrets: ${missingFields.join(", ")}. ` +
        `Ensure all required fields are present in AWS Secrets Manager (production) or .env (development).`,
    );
  }
}
