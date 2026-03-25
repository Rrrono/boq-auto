export type FirebaseWebConfig = {
  apiKey: string;
  authDomain: string;
  projectId: string;
  storageBucket?: string;
  messagingSenderId?: string;
  appId: string;
};

function fromJsonEnv(value: string | undefined): FirebaseWebConfig | null {
  if (!value?.trim()) {
    return null;
  }
  try {
    const parsed = JSON.parse(value) as Partial<FirebaseWebConfig>;
    if (!parsed.apiKey || !parsed.authDomain || !parsed.projectId || !parsed.appId) {
      return null;
    }
    return {
      apiKey: parsed.apiKey,
      authDomain: parsed.authDomain,
      projectId: parsed.projectId,
      storageBucket: parsed.storageBucket,
      messagingSenderId: parsed.messagingSenderId,
      appId: parsed.appId,
    };
  } catch {
    return null;
  }
}

export function getFirebaseWebConfig(): FirebaseWebConfig | null {
  const jsonConfig =
    fromJsonEnv(process.env.NEXT_PUBLIC_FIREBASE_WEBAPP_CONFIG) ??
    fromJsonEnv(process.env.FIREBASE_WEBAPP_CONFIG);
  if (jsonConfig) {
    return jsonConfig;
  }

  const apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY;
  const authDomain = process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN;
  const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
  const appId = process.env.NEXT_PUBLIC_FIREBASE_APP_ID;
  if (!apiKey || !authDomain || !projectId || !appId) {
    return null;
  }

  return {
    apiKey,
    authDomain,
    projectId,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    appId,
  };
}
