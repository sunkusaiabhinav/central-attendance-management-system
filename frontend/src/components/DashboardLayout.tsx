import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";

/** Main layout wrapper — renders Sidebar + page content */
export function DashboardLayout() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      {/* Main content area offset by sidebar width */}
      <main className="flex-1 ml-64 min-h-screen">
        <div className="p-8 animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
