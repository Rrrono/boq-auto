"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { initializeApp, type FirebaseApp, getApps } from "firebase/app";
import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type User,
} from "firebase/auth";

import type { FirebaseWebConfig } from "../lib/firebase-config";


type AuthContextValue = {
  configured: boolean;
  loading: boolean;
  user: User | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOutUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);


function getFirebaseApp(config: FirebaseWebConfig): FirebaseApp {
  return getApps()[0] ?? initializeApp(config);
}


export function AuthProvider({
  children,
  firebaseConfig,
}: {
  children: React.ReactNode;
  firebaseConfig: FirebaseWebConfig | null;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(firebaseConfig));

  useEffect(() => {
    if (!firebaseConfig) {
      setLoading(false);
      return;
    }
    const auth = getAuth(getFirebaseApp(firebaseConfig));
    return onAuthStateChanged(auth, (nextUser) => {
      setUser(nextUser);
      setLoading(false);
    });
  }, [firebaseConfig]);

  const value = useMemo<AuthContextValue>(
    () => ({
      configured: Boolean(firebaseConfig),
      loading,
      user,
      async signIn(email: string, password: string) {
        if (!firebaseConfig) {
          throw new Error("Firebase Auth is not configured for this deployment.");
        }
        const auth = getAuth(getFirebaseApp(firebaseConfig));
        await signInWithEmailAndPassword(auth, email, password);
      },
      async signOutUser() {
        if (!firebaseConfig) {
          return;
        }
        const auth = getAuth(getFirebaseApp(firebaseConfig));
        await signOut(auth);
      },
    }),
    [firebaseConfig, loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}


export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
