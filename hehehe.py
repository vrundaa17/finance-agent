# from mcp.server.fastmcp import FastMCP

# mcp = FastMCP("calc")

# tasks =[]

# @mcp.tool()
# def add_task(task : str):
#     """Add a new todo task."""
#     tasks.append({
#         "task" :task,
#         "done" : False
#     })
#     return "Task added"

# @mcp.tool()
# def list_task():
#     """Show all the task"""
#     return tasks

# @mcp.tool()
# def complete_task(index: int):
#     """Mark a task as completed."""
#     if index < 0 or index >= len(tasks):
#         return "Task not found"
#     tasks[index]["done"] = True

#     return "Task completed"

# @mcp.tool()
# def delete_task(index: int):
#     """Delete a todo task."""
#     if index < 0 or index >= len(tasks):
#         return "Task not found"

#     tasks.pop(index)
#     return "Task deleted"

# @mcp.tool()
# def clear_tasks():
#     """Remove all tasks."""
#     tasks.clear()
#     return "All tasks c;ear"

# @mcp.resource("todo://stats")
# def todo_stats():
#     return {
#         "total": len(tasks),
#         "completed": len([t for t in tasks if t["done"]])
#     }
# @mcp.resource("todo://all")
# def all_tasks():
#     """Return all current tasks."""
#     return tasks
    
# if __name__ == "__main__":
#     mcp.run()

# a="hello"
# b =[]
# s=len(a)
# # print(s)
# while s>0:
#     b.append(a[s-1])
#     s=s-1
# print("".join(b))
# def add_items(item,items=[]):
#     print(id(items))
#     items.append(item)
#     return items

# add_items("a")
# add_items("b")
# sum_list([1,2,3,4])
def sum_list(n):
    len_list = len(l)-1
    if len(n)==0:
        return 
    else:
        return n+sum_list(len_list-1)
l=[1,2,3,4]