import { NavLink } from "react-router-dom";
import { ChatIcon, DayIcon, HomeIcon, PersonIcon } from "./Icons";

const LINKS = [
  { to: "/", label: "Home", Icon: HomeIcon },
  { to: "/chat", label: "Chat", Icon: ChatIcon },
  { to: "/my-day", label: "My day", Icon: DayIcon },
  { to: "/about-me", label: "About me", Icon: PersonIcon },
];

export default function NavBar() {
  return (
    <nav className="nav" aria-label="Main">
      <span className="nav__brand">Milo</span>
      <ul className="nav__list">
        {LINKS.map(({ to, label, Icon }) => (
          <li key={to}>
            {/* NavLink marks the current screen, so it can be highlighted */}
            <NavLink to={to} end className="nav__link">
              <Icon />
              <span>{label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
