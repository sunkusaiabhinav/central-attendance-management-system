import { useEffect, useState, type FormEvent } from "react";
import {
  UserPlus,
  Search,
  Shield,
  Building,
  X,
} from "lucide-react";
import { employeesApi } from "@/api/employees";
import { formatDate } from "@/utils";
import type { Employee, EmployeeCreateRequest } from "@/types";

export function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterDept, setFilterDept] = useState("ALL");
  const [showAddModal, setShowAddModal] = useState(false);

  // Form State
  const [formData, setFormData] = useState<EmployeeCreateRequest>({
    full_name: "",
    email: "",
    department: "",
    password: "",
    role: "EMPLOYEE",
  });
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchEmployees = async () => {
    setIsLoading(true);
    try {
      const res = await employeesApi.list({ page: 1, page_size: 100 });
      setEmployees(res.employees);
    } catch (err) {
      console.error("Failed to fetch employees", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployees();
  }, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError(null);
    try {
      await employeesApi.create(formData);
      setShowAddModal(false);
      setFormData({
        full_name: "",
        email: "",
        department: "",
        password: "",
        role: "EMPLOYEE",
      });
      fetchEmployees();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to create employee. Please check input values.";
      setFormError(msg);
    } finally {
      setFormLoading(false);
    }
  };

  const toggleStatus = async (emp: Employee) => {
    try {
      await employeesApi.updateStatus(emp.id, !emp.is_active);
      fetchEmployees();
    } catch (err) {
      console.error("Failed to toggle status", err);
    }
  };

  const departments = Array.from(new Set(employees.map((e) => e.department))).filter(Boolean);

  const filteredEmployees = employees.filter((e) => {
    const matchesSearch =
      e.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDept = filterDept === "ALL" || e.department === filterDept;
    return matchesSearch && matchesDept;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Page Header ── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            Employee <span className="text-gradient">Management</span>
          </h1>
          <p className="page-subtitle">
            Configure employee directory, access tiers, and departmental assignments
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn-primary text-xs gap-1.5"
        >
          <UserPlus className="w-3.5 h-3.5" />
          Add Employee
        </button>
      </div>

      {/* ── Search & Filter Controls ── */}
      <div className="glass-card p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Building className="w-4 h-4 text-brand-400" />
          <select
            value={filterDept}
            onChange={(e) => setFilterDept(e.target.value)}
            className="input-field py-1.5 px-3 text-xs w-44"
          >
            <option value="ALL">All Departments</option>
            {departments.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        <div className="relative min-w-[260px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search name or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-field py-1.5 pl-8 text-xs"
          />
        </div>
      </div>

      {/* ── Employee Directory Table ── */}
      <div className="table-container">
        <div className="px-6 py-4 border-b border-white/8 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-100">
            Workforce Roster ({filteredEmployees.length})
          </h2>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            <div className="w-6 h-6 border-2 border-brand-500/40 border-t-brand-500 rounded-full animate-spin mx-auto mb-2" />
            Loading employees...
          </div>
        ) : filteredEmployees.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No employees found matching the filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header">Name & Email</th>
                  <th className="table-header">Department</th>
                  <th className="table-header">Role</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Created</th>
                  <th className="table-header text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredEmployees.map((emp) => (
                  <tr key={emp.id} className="table-row">
                    <td className="table-cell">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-brand-600 to-purple-600 flex items-center justify-center font-bold text-xs text-white">
                          {emp.full_name.charAt(0)}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-200">{emp.full_name}</p>
                          <p className="text-slate-400 text-xs">{emp.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="table-cell text-slate-300 font-medium">
                      {emp.department}
                    </td>
                    <td className="table-cell">
                      <span
                        className={`badge ${
                          emp.role === "ADMIN"
                            ? "bg-purple-500/15 text-purple-300 border border-purple-500/30"
                            : "bg-blue-500/15 text-blue-300 border border-blue-500/30"
                        }`}
                      >
                        <Shield className="w-3 h-3 mr-1" />
                        {emp.role}
                      </span>
                    </td>
                    <td className="table-cell">
                      {emp.is_active ? (
                        <span className="badge-success">Active</span>
                      ) : (
                        <span className="badge-neutral">Deactivated</span>
                      )}
                    </td>
                    <td className="table-cell text-xs text-slate-400">
                      {formatDate(emp.created_at)}
                    </td>
                    <td className="table-cell text-right">
                      <button
                        onClick={() => toggleStatus(emp)}
                        className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
                          emp.is_active
                            ? "border-red-500/30 text-red-400 hover:bg-red-500/10"
                            : "border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
                        }`}
                      >
                        {emp.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Add Employee Modal ── */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="glass-card max-w-md w-full p-6 relative border border-white/20 shadow-glow">
            <button
              onClick={() => setShowAddModal(false)}
              className="absolute right-4 top-4 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-brand-600/20 text-brand-400 flex items-center justify-center">
                <UserPlus className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-100">Add New Employee</h2>
                <p className="text-xs text-slate-400">Register employee in system</p>
              </div>
            </div>

            {formError && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="input-label">Full Name</label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  placeholder="e.g. Sarah Connor"
                  className="input-field"
                />
              </div>

              <div>
                <label className="input-label">Email Address</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="e.g. sarah@cyberdyne.io"
                  className="input-field"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="input-label">Department</label>
                  <input
                    type="text"
                    required
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    placeholder="Engineering"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="input-label">Role</label>
                  <select
                    value={formData.role}
                    onChange={(e) =>
                      setFormData({ ...formData, role: e.target.value as "ADMIN" | "EMPLOYEE" })
                    }
                    className="input-field"
                  >
                    <option value="EMPLOYEE">EMPLOYEE</option>
                    <option value="ADMIN">ADMIN</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="input-label">Initial Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="Min. 8 characters"
                  className="input-field"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="btn-primary text-xs"
                >
                  {formLoading ? "Creating..." : "Save Employee"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
