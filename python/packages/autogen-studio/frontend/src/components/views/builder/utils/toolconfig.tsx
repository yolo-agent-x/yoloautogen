import React from "react";
import {fetchJSON, getServerUrl,} from "../../../utils";
import {Button, Input, message} from "antd";
import {ITool} from "../../../types";
import {ControlRowView} from "../../../atoms";
import TextArea from "antd/es/input/TextArea";
import {appContext} from "../../../../hooks/provider";

export const ToolConfigView = ({
  tool,
  setTool,
  close,
}: {
  tool: ITool;
  setTool: (newModel: ITool) => void;
  close: () => void;
}) => {
  const [loading, setLoading] = React.useState(false);

  const serverUrl = getServerUrl();
  const { user } = React.useContext(appContext);
  const createToolUrl = `${serverUrl}/tools`;

  const createTool = (tool: ITool) => {
    setLoading(true);
    tool.user_id = user?.email;
    const payLoad = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({...tool,
      "args_info": JSON.parse(tool.args_info || "{}")
      }),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        setTool({...data.data, args_info: JSON.stringify(data.data.args_info)});
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      message.error(err.message);
      setLoading(false);
    };
    const onFinal = () => {
      setLoading(false);
      setControlChanged(false);
    };
    fetchJSON(createToolUrl, payLoad, onSuccess, onError, onFinal);
  };

  const [controlChanged, setControlChanged] = React.useState<boolean>(false);

  const updateToolConfig = (key: string, value: any) => {
    if (tool) {
      const updatedTool = { ...tool, [key]: value };
      //   setSkill(updatedModelConfig);
      setTool(updatedTool);
    }
    setControlChanged(true);
  };

  return (
    <div className="relative ">
      {tool && (
        <div style={{ minHeight: "65vh" }}>
          <div className="flex gap-3">
            <div className="w-72 ">
              <div className="">
                <ControlRowView
                  title="Name"
                  className=""
                  description="Tool name, should match function name"
                  value={tool?.name || ""}
                  control={
                    <Input
                      className="mt-2 w-full"
                      value={tool?.name}
                      onChange={(e) => {
                        updateToolConfig("name", e.target.value);
                      }}
                    />
                  }
                />

                <ControlRowView
                  title="Description"
                  className="mt-4"
                  description="Description of the tool"
                  value={tool?.description || ""}
                  control={
                    <TextArea
                      className="mt-2 w-full"
                      value={tool?.description}
                      onChange={(e) => {
                        updateToolConfig("description", e.target.value);
                      }}
                    />
                  }
                />
                <ControlRowView
                    title="Method"
                    className="mt-4"
                    description="Method of the tool"
                    value={tool?.method || ""}
                    control={
                      <TextArea
                          className="mt-2 w-full"
                          value={tool?.method}
                          onChange={(e) => {
                            updateToolConfig("method", e.target.value);
                          }}
                      />
                    }
                />
                <ControlRowView
                    title="url"
                    className="mt-4"
                    description="Url of the tool"
                    value={tool?.url || ""}
                    control={
                      <TextArea
                          className="mt-2 w-full"
                          value={tool?.url}
                          onChange={(e) => {
                            updateToolConfig("url", e.target.value);
                          }}
                      />
                    }
                />
                <ControlRowView
                    title="args info"
                    className="mt-4"
                    description="Args information of the tool"
                    value={tool?.args_info || ""}
                    control={
                      <TextArea
                          className="mt-2 w-full"
                          value={tool?.args_info}
                          onChange={(e) => {
                            updateToolConfig("args_info", e.target.value);
                          }}
                      />
                    }
                />
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="w-full mt-4 text-right">
        {/* <Button
          key="test"
          type="primary"
          loading={loading}
          onClick={() => {
            if (skill) {
              testModel(skill);
            }
          }}
        >
          Test Model
        </Button> */}

        {
          <Button
            className="ml-2"
            key="save"
            type="primary"
            onClick={() => {
              if (tool) {
                createTool(tool);
                setTool(tool);
              }
            }}
          >
            {tool?.id ? "Update Tool" : "Save Tool"}
          </Button>
        }

        <Button
          className="ml-2"
          key="close"
          type="default"
          onClick={() => {
            close();
          }}
        >
          Close
        </Button>
      </div>
    </div>
  );
};
