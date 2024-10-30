import {InformationCircleIcon, PlusIcon, TrashIcon,} from "@heroicons/react/24/outline";
import {Button, message, Modal} from "antd";
import * as React from "react";
import {IStatus, ITool} from "../../types";
import {appContext} from "../../../hooks/provider";
import {fetchJSON, getServerUrl, timeAgo, truncateText,} from "../../utils";
import {BounceLoader, Card, CardHoverBar, LoadingOverlay,} from "../../atoms";
import {ToolConfigView} from "./utils/toolconfig";

const ToolsView = ({}: any) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const listToolsUrl = `${serverUrl}/tools?user_id=${user?.email}`;
  const saveToolsUrl = `${serverUrl}/tools`;

  const [tools, setTools] = React.useState<ITool[] | null>([]);
  const [selectedTool, setSelectedTool] = React.useState<any>(null);

  const [showToolModal, setShowToolModal] = React.useState(false);
  const [showNewToolModal, setShowNewToolModal] = React.useState(false);

  const [newTool, setNewTool] = React.useState<ITool | null>();

  const deleteTool = (tool: ITool) => {
    setError(null);
    setLoading(true);
    // const fetch;
    const deleteToolUrl = `${serverUrl}/tools/delete?user_id=${user?.email}&tool_id=${tool.id}`;
    const payLoad = {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user?.email,
        tool: tool,
      }),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        fetchTools();
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(deleteToolUrl, payLoad, onSuccess, onError);
  };

  const fetchTools = () => {
    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        // message.success(data.message);
        const tools = data.data.map( (d:any) => {
          return {
            ...d,
            args_info: JSON.stringify(d.args_info)
          }
        })

        setTools(tools);
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(listToolsUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchTools();
    }
  }, []);

  const toolRows = (tools || []).map((tool: ITool, i: number) => {
    const cardItems = [
      {
        title: "Delete",
        icon: TrashIcon,
        onClick: (e: any) => {
          e.stopPropagation();
          deleteTool(tool);
        },
        hoverText: "Delete",
      },
    ];
    return (
      <li key={"toolrow" + i} className=" " style={{ width: "200px" }}>
        <div>
          {" "}
          <Card
            className="h-full p-2 cursor-pointer group"
            title={truncateText(tool.name, 25)}
            onClick={() => {
              setSelectedTool(tool);
              setShowToolModal(true);
            }}
          >
            <div
              style={{ minHeight: "65px" }}
              className="my-2   break-words"
              aria-hidden="true"
            >
              {" "}
              {tool.description
                ? truncateText(tool.description || "", 70)
                : truncateText(tool.name || "", 70)}
            </div>
            <div
              aria-label={`Updated ${timeAgo(tool.updated_at || "")}`}
              className="text-xs"
            >
              {timeAgo(tool.updated_at || "")}
            </div>
            <CardHoverBar items={cardItems} />
          </Card>
          <div className="text-right mt-2"></div>
        </div>
      </li>
    );
  });

  const ToolModal = ({
    tool,
    setTool,
    showToolModal,
    setShowToolModal,
    handler,
  }: {
    tool: ITool | null;
    setTool: any;
    showToolModal: boolean;
    setShowToolModal: any;
    handler: any;
  }) => {
    const [localTool, setLocalTool] = React.useState<ITool | null>(tool);
    const closeModal = () => {
      setTool(null);
      setShowToolModal(false);
      if (handler) {
        handler(tool);
      }
    };

    return (
      <Modal
        title={
          <>
            Tool Specification{" "}
            <span className="text-accent font-normal">{localTool?.name}</span>{" "}
          </>
        }
        width={800}
        open={showToolModal}
        onCancel={() => {
          setShowToolModal(false);
        }}
        footer={[]}
      >
        {localTool && (
          <ToolConfigView
            tool={localTool}
            setTool={setLocalTool}
            close={closeModal}
          />
        )}
      </Modal>
    );
  };

  const defaultTool = {
    name: "",
    description: "",
    method: "",
    url: "",
    args_info: "{}"
  } as ITool

    return (
    <div className=" text-primary ">
      <ToolModal
        tool={selectedTool}
        setTool={setSelectedTool}
        showToolModal={showToolModal
      }
        setShowToolModal={setShowToolModal}
        handler={(tool: ITool) => {
          fetchTools();
        }}
      />

      <ToolModal
        tool={newTool || defaultTool}
        setTool={setNewTool}
        showToolModal={showNewToolModal}
        setShowToolModal={setShowNewToolModal}
        handler={(tool: ITool) => {
          fetchTools();
        }}
      />

      <div className="mb-2   relative">
        <div className="">
          <div className="flex mt-2 pb-2 mb-2 border-b">
            <ul className="flex-1   font-semibold mb-2 ">
              {" "}
              Tools ({toolRows.length}){" "}
            </ul>
            <div>
              <Button
                type="primary"
                onClick={() => {
                  setShowNewToolModal(true);
                }}
              >
                <PlusIcon className="w-5 h-5 inline-block mr-1" />
                New Tool
              </Button>
            </div>
          </div>
          <div className="text-xs mb-2 pb-1  ">
            {" "}
            Tools are functions that agents can use to solve tasks.{" "}
          </div>
          {tools && tools.length > 0 && (
            <div
              // style={{ height: "400px" }}
              className="w-full  relative"
            >
              <LoadingOverlay loading={loading} />
              <div className="   flex flex-wrap gap-3">{toolRows}</div>
            </div>
          )}

          {tools && tools.length === 0 && !loading && (
            <div className="text-sm border mt-4 rounded text-secondary p-2">
              <InformationCircleIcon className="h-4 w-4 inline mr-1" />
              No tools found. Please create a new tool.
            </div>
          )}
          {loading && (
            <div className="  w-full text-center">
              {" "}
              <BounceLoader />{" "}
              <span className="inline-block"> loading .. </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ToolsView;
