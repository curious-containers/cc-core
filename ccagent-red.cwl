baseCommand:
- ccagent
- red
- --outputs
- --debug
- --format=json
class: CommandLineTool
cwlVersion: v1.0
doc: Run an experiment as described in a REDFILE.
inputs:
  red_file:
    doc: REDFILE (json or yaml) containing an experiment description.
    inputBinding:
      position: 0
    type: File
  variables:
    doc: VARFILE (json or yaml) containing key-value pairs for variables in REDFILE.
    inputBinding:
      prefix: --variables=
      separate: false
    type: File?
  leave_directories:
    doc: Leave temporary inputs and working directories.
    inputBinding:
      prefix: --leave-directories
    type: boolean?
outputs:
  debug:
    doc: Structured debug info in JSON format.
    type: stdout

stdout: debug.json
