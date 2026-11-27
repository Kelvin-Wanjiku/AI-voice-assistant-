import { useEffect, useRef } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import NavBar from "./components/NavBar";
import ReminderBanner from "./components/ReminderBanner";
import AboutMeScreen from "./screens/AboutMeScreen";
import ChatScreen from "./screens/ChatScreen";
import HomeScreen from "./screens/HomeScreen";
import MyDayScreen from "./screens/MyDayScreen";

const TITLES: Record<string, string> = {
  "/": "Home",
  "/chat": "Chat",
  "/my-day": "My day",
  "/about-me": "About me",
};

export default function App() {
  const { pathname } = useLocation();
  const previousPath = useRef(pathname);

  // When the screen changes: update the browser tab title, go back to the top,
  // and move keyboard/screen-reader focus to the new screen's heading.
  // (Not on the very first load, so the first Tab press still reaches the menu.)
  useEffect(() => {
    document.title = `${TITLES[pathname] ?? "Milo"} · Milo`;
    if (previousPath.current === pathname) return;
    previousPath.current = pathname;
    window.scrollTo(0, 0);
    document.querySelector<HTMLElement>("main h1")?.focus();
  }, [pathname]);

  return (
    <div className="app">
      <NavBar />
      <ReminderBanner />
      <main className="screen">
        <Routes>
          <Route path="/" element={<HomeScreen />} />
          <Route path="/chat" element={<ChatScreen />} />
          <Route path="/my-day" element={<MyDayScreen />} />
          <Route path="/about-me" element={<AboutMeScreen />} />
          {/* Any unknown address goes back to Home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
