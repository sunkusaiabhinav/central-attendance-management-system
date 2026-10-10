import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Clock,
  Users,
  BarChart3,
  ShieldCheck,
  LogOut,
  CalendarCheck,
  Building2,
  ChevronRight,
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { cn } from "@/utils";

const adminNavItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard", end: true },
  { to: "/attendance", icon: Clock, label: "Attendance" },
  { to: "/employees", icon: Users, label: "Employees" },
  { to: "/reports", icon: BarChart3, label: "Reports" },
  { to: "/compliance", icon: ShieldCheck, label: "Compliance" },
];

const employeeNavItems = [
  { to: "/my-attendance", icon: CalendarCheck, label: "My Attendance", end: true },
  { to: "/compliance", icon: ShieldCheck, label: "My Compliance" },
];

export function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const isAdmin = user?.role === "ADMIN";
  const navItems = isAdmin ? adminNavItems : employeeNavItems;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside className="fixed inset-y-0 left-0 w-64 flex flex-col z-40">
      {/* Background */}
      <div className="absolute inset-0 bg-surface-950/95 backdrop-blur-xl border-r border-white/8" />

      <div className="relative flex flex-col h-full px-4 py-6">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8 px-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-glow-sm flex-shrink-0">
            <Building2 className="w-5 h-5 text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-slate-100 leading-tight truncate">
              Central AMS
            </p>
            <p className="text-xs text-slate-500 leading-tight">
              Attendance Management
            </p>
          </div>
        </div>

        {/* Role Badge */}
        <div className="mx-2 mb-6 px-3 py-2 rounded-lg bg-brand-600/15 border border-brand-500/25">
          <p className="text-xs font-medium text-brand-300 uppercase tracking-wider">
            {isAdmin ? "🛡️ Admin Portal" : "👤 Employee Portal"}
          </p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1">
          <p className="px-3 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Navigation
          </p>
          {navItems.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn("sidebar-link", isActive && "active")
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1">{label}</span>
              <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-50 transition-opacity" />
            </NavLink>
          ))}
        </nav>

        {/* User Info + Logout */}
        <div className="mt-4 pt-4 border-t border-white/8 space-y-3">
          {/* User Card */}
          <div className="px-3 py-2.5 rounded-xl bg-white/5 border border-white/8">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-purple-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                {user?.full_name?.charAt(0)?.toUpperCase() ?? "U"}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-slate-200 truncate">
                  {user?.full_name ?? "Loading..."}
                </p>
                <p className="text-xs text-slate-500 truncate">{user?.email}</p>
              </div>
            </div>
          </div>

          {/* Logout Button */}
          <button
            id="logout-btn"
            onClick={handleLogout}
            className="sidebar-link w-full text-red-400 hover:text-red-300 hover:bg-red-500/10"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
