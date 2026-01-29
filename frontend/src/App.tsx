import { Outlet, NavLink } from "react-router-dom"
import { LayoutDashboard, Settings, Trash2 } from "lucide-react"
import { cn } from "./lib/utils"

function App() {
  const navItems = [
    { to: "/", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/settings", icon: Settings, label: "Settings" },
    { to: "/trash", icon: Trash2, label: "Trash" },
  ]

  return (
    <div className="min-h-screen bg-[hsl(var(--background))]">
      <nav className="border-b border-[hsl(var(--border))] bg-[hsl(var(--card))]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <span className="text-xl font-bold text-[hsl(var(--primary))]">
                DietTube
              </span>
              <span className="ml-2 text-sm text-[hsl(var(--muted-foreground))]">
                Give your video library a diet
              </span>
            </div>
            <div className="flex space-x-4">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors",
                      isActive
                        ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                        : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--accent))] hover:text-[hsl(var(--accent-foreground))]"
                    )
                  }
                  end={item.to === "/"}
                >
                  <item.icon className="w-4 h-4 mr-2" />
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}

export default App
