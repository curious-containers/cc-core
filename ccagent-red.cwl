baseCommand:
- ccagent
- red
- --outputs
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
      prefix: --variables
    type: File?
  debug:
    doc: Write debug info, including detailed exceptions, to stdout.
    inputBinding:
      prefix: --debug
    type: boolean?
  format:
    doc: Specify FORMAT for generated data as one of [json, yaml, yml]. Default is yaml.
      inputBinding:
        prefix: --format
      type: string?
  leave_directories:
    doc: Leave temporary inputs and working directories.
    inputBinding:
      prefix: --leave-directories
    type: boolean?
outputs:
  debug:
    doc: Structured debug info in YAML or JSON format.
    type: stdout?
  error:
    doc: Human readable error message.
    type: stderr?

stdout: debug.txt
stderr: error.txt
