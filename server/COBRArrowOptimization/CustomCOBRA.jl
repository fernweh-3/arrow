module CustomCOBRA
using JuMP
using Gurobi
using GLPK
using CPLEX
# Determine the directory of this script
script_path = @__FILE__
script_dir = dirname(script_path)

# Include additional scripts from the same directory
include(joinpath(script_dir, "solve.jl"))

end
