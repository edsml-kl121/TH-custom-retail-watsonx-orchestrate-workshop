### Instructions

This lab shows how to create an agent and a simple flow that accepts a job position from the user and generates job criteria for resume screening.

Prerequisites
- Access to the Studio UI where agents and flows are created.

Steps

1) Create the agent
- Create a new agent named `resume_screening_agent`.
- Change the agent style from `Default` to `ReAct` to make the agent more interactive.

![Switch agent style from Default to ReAct](images/image1.png)

2) Add a tool that uses a new flow
- In the agent settings, open the Toolset section and click `Add tool`.
- Choose `Create a new flow`.

![Click add tool](images/image2.png)
![Click create a new flow](images/image3.png)

- Click the flow title (usually `Untitled`) in the top-left to open the flow settings.

![Open flow settings](images/image4.png)

- Change the tool name to `resume_screening_tool` and set the description to `Use this tool to get resume scoring`.
- Click Save.

![Set tool name and description](images/image5.png)

#### Create the workflow
1) Add a User Activity node
- Hover over the connection line between Start and End until a plus (+) appears.
- Click the plus icon and select `User activity` from the menu.

![Add user activity node](images/image6.png)
![User activity added](images/image7.png)

2) Ask the user for the job position
- Edit the User Activity node's display name to: "Please enter the job position"

![Edit display name](images/image8.png)

3) Add a Generative Prompt inside the User Activity
- Drag a `Generative prompt` into the User Activity node.
- Rename it to `Generative Job Position`.
- Click Edit to accept input from the previous step.

![Drag generative prompt to user activity](images/image10.png)

named it as **Generatative prompt expected_criteria**

![Change Generative prompt named as Generative prompt expected_criteria](images/Generative_prompt_expected_criteria.png)

Configuration for the Generative Prompt

- Input variable:
  - Name: `job_position`
  - Description: `Job position which user interested`
  - Click `Add` to save the input variable.

![Click Edit Generative prompt setting](images/image11.png)

![add input variable type string](images/image12.png)

![Edit name and description of input variable](images/image13.png)

- System prompt (use the exact rules below):

```
Rules:
1. Answer in JSON format only. 
2. You will get job position from user query and you will return only related information for that job position. 
3. Do NOT ask any question from user. They will give you a job position and you will return JSON only.
4. Ensure all fields are filled with appropriate data and avoid leaving any blank (e.g., 'not specified').
```

- User prompt (what the flow will send to the model):
```
job position:
```

You should see similar to this when the prompt is configured:

![prompt when configured](images/image14.png)

![Click Select Variable](images/image15.png)

![Select job_position](images/image16.png)

![Output when add job_position variable](images/image17.png)

- Now will custom output of this generative prompt

![Click open Output as Object](images/image18.png)

![Click add object definition](images/image19.png)

Change object output name to ```expected_criteria ``` with ```expected_criteria align with job``` as descripiton

with this JSON schema
```
{
  "skills": {
    "type": "string"
  },
  "experience": {
    "type": "string"
  }
}
```

![Click Save button](images/image20.png)

- Change the model to ``` llama-4-maverick-17b-128e-instruct-fp8 ```, Test Generative output :

![Change the model](images/image21.png)

![Click edit test value](images/image22.png)

![Set values as Sales](images/image23.png)

![Click Generate response](images/image24.png)

![Configured prompt example](images/image25.png)

Output would be simliar like this

![Configured prompt example](images/image26.png)

4) Now add new flow to upload candidate's resume 

![upload 1st candiate's resume](images/image26.png)

![upload 1st candiate's resume](images/image27.png)

change name to  **Resume uploader1**

![upload 1st candiate's resume](images/image28.png)

5) Add a Document Extractor  inside the User Activity
- Drag a `Document Extractor` into the User Activity node.
- Rename it to `Resume extractor1`.

![upload 1st candiate's resume](images/image29.png)
