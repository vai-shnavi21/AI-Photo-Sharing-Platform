import API from "./api";
let activeSession = null;
export const saveSession = ({token,user}) => { activeSession = { token, user }; window.dispatchEvent(new Event("authchange")); };
export const session = () => activeSession?.user || null;
export const signOut = () => { activeSession = null; window.dispatchEvent(new Event("authchange")); };
export const authHeaders = () => activeSession?.token ? {Authorization:`Bearer ${activeSession.token}`} : {};
export const authToken = () => activeSession?.token || null;
export const googleLogin = async credential => { const {data}=await API.post("/auth/google",{credential}); saveSession(data); return data.user; };
