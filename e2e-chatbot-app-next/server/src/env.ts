import dotenv from 'dotenv';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Get the directory name of the current module
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Check if running in test mode
const TEST_MODE = process.env.TEST_MODE;

if (!TEST_MODE) {
  // Workspace .env (e2e-chatbot-app-next)
  dotenv.config({ path: path.resolve(__dirname, '../..', '.env') });
  // Repo root .env and .env.local (so API_PROXY from project root is available)
  const repoRoot = path.resolve(__dirname, '../../..');
  dotenv.config({ path: path.join(repoRoot, '.env') });
  dotenv.config({ path: path.join(repoRoot, '.env.local'), override: true });
}
