import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API, { API_BASE_URL } from "../services/api";
import { saveSession } from "../services/auth";

export default function Auth() {
  const [mode, setMode] = useState("signin");
  const [form, setForm] = useState({ full_name: "", email: "", password: "", captcha_answer: "" });
  const [captcha, setCaptcha] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const loadCaptcha = async () => {
    try { setCaptcha((await API.get("/auth/captcha")).data); }
    catch { setError("Could not load the verification question. Please refresh the page."); }
  };

  useEffect(() => {
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
    if (!token) return;
    API.get("/auth/me", { headers: { Authorization: `Bearer ${token}` } })
      .then(({ data }) => { saveSession({ token, user: data }); window.history.replaceState(null, "", window.location.pathname); nav("/"); })
      .catch(() => setError("Google sign-in could not be completed. Please try again."));
  }, [nav]);

  useEffect(() => { if (mode === "signup") loadCaptcha(); }, [mode]);

  const changeMode = () => {
    setMode(mode === "signin" ? "signup" : "signin");
    setError("");
    setForm({ full_name: "", email: "", password: "", captcha_answer: "" });
  };

  const submit = async (event) => {
    event.preventDefault();
    setError(""); setLoading(true);
    try {
      const payload = mode === "signup"
        ? { ...form, captcha_id: captcha?.captcha_id, captcha_answer: Number(form.captcha_answer) }
        : { email: form.email, password: form.password };
      const { data } = await API.post(mode === "signup" ? "/auth/signup" : "/auth/signin", payload);
      saveSession(data); nav("/");
    } catch (err) { setError(err.response?.data?.detail || "We could not sign you in. Please try again."); }
    finally { setLoading(false); }
  };

  return <main className="auth-page">
    <section className="auth-card">
      <p className="eyebrow">AI EVENT PHOTO SHARING</p>
      <h1>{mode === "signup" ? "Create your account" : "Welcome back"}</h1>
      <p className="auth-intro">{mode === "signup" ? "Save and revisit the photos that matter to you." : "Sign in to manage your personal gallery."}</p>
      <button
        className="google-button"
        type="button"
        onClick={() => window.location.assign(
          `${API_BASE_URL}/auth/google/${mode === "signup" ? "signup-login" : "login"}`
        )}
      >
        <span className="google-mark">G</span> {mode === "signup" ? "Sign up with Google" : "Sign in with Google"}
      </button>
      <div className="divider"><span>or continue with email</span></div>
      <form onSubmit={submit} noValidate>
        {mode === "signup" && <label>Full name<input autoComplete="name" placeholder="Your name" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>}
        <label>Email address<input type="email" autoComplete="email" placeholder="you@example.com" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
        <label>Password<input type="password" autoComplete={mode === "signup" ? "new-password" : "current-password"} placeholder="At least 8 characters" minLength="8" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
        {mode === "signup" && <div className="captcha-panel"><div><strong>Quick verification</strong><span>{captcha?.question || "Loading question…"}</span></div><input aria-label="CAPTCHA answer" type="number" required value={form.captcha_answer} onChange={(e) => setForm({ ...form, captcha_answer: e.target.value })} /><button className="icon-button" type="button" onClick={loadCaptcha} aria-label="New question">↻</button></div>}
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" disabled={loading || (mode === "signup" && !captcha)}>{loading ? "Please wait…" : mode === "signup" ? "Create account" : "Sign in"}</button>
      </form>
      <p className="switch-auth">{mode === "signup" ? "Already have an account?" : "New here?"} <button type="button" onClick={changeMode}>{mode === "signup" ? "Sign in" : "Create an account"}</button></p>
    </section>
  </main>;
}
