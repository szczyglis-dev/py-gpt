# Example GUI tool

This `tool` Add-on adds a real action to the **Tools** menu and opens a Qt dialog. It also listens for `CTX_SELECT`, showing how GUI tools can observe the same application event stream as built-in tools.

## Try it

Install the directory, restart PyGPT, then choose **Tools -> External add-on example**. Switch conversations and open the action again to see the selected context ID update.

Use this pattern for desktop utilities, dialogs, reusable widgets and optional output tabs. GUI callbacks run in the application process, so follow normal Qt thread-affinity rules.
