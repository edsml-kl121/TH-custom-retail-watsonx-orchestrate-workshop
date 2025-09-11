### Instructions

This lab shows how to create an agent and a simple flow that accepts a job position from the user and compares candidates' resumes to determine who aligns better with the job position. The output will be a score for each candidate, indicating how well their resume matches the job position.

Prerequisites
- Access to the Studio UI where agents and flows are created.

## Steps
1 Create the agent<br/>
    1.1 Choose `create from scratch`<br>
    1.2 Create a new agent named `resume_screening_agent` <br>
    1.3 Set the description to :<br>
    `This agent using when need to compare candidate's resume align with job position the output will be scoring of each candidate resume` 
---

2. Add a Tool that Using a New Flow <br>
    2.1 In the agent settings, open the Toolset section and click **Add tool**.<br>
    2.2 Choose **Create a new flow**.<br>
    ![Click add tool](images/image2.png)
    ![Click create a new flow](images/image3.png)

    2.3 Click the flow title (usually `Untitled`) in the top-left to open the flow settings.
    ![Open flow settings](images/image4.png)

    2.4 Change the tool name to `resume_screening_tool` and set the description to `This tool using when user need to compare candidate's resume`.<br>
    2.5 Click Save.

    ![Set tool name and description](images/image5.png)
---

#### Create the workflow
1) Add a User Activity node
- Hover over the connection line between Start and End until a plus (+) appears.
- Click the plus icon and select `User activity` from the menu.

![Add user activity node](images/image6.png)
![User activity added](images/image7.png)

---

2) Ask the user for the Job Position
- Edit the User Activity node's display name to: `กรุณาใส่ตำแหน่งงาน`

![Add Collect text from user](images/image8.png)

![Change display name to please provide job position](images/image9.png)

---

3) Add a Generative Prompt inside the User Activity
- Drag a **Generative prompt** into the User Activity node.
- Rename it to `Generative Job Position`.
- Click Edit to accept input from the previous step.

![Drag generative prompt to user activity](images/image10.png)

- rename it to **Generatative prompt expected_criteria**

![Change Generative prompt named as Generative prompt expected_criteria](images/Generative_prompt_expected_criteria.png)

---

4) Configuration for the Generative Prompt<br>
  4.1 Input variable:
    - Name: `job_position`
    - Description: `Job position which user interested`
    - Click `Add` to save the input variable.

![Click Edit Generative prompt setting](images/image11.png)

![add input variable type string](images/image12.png)

![Edit name and description of input variable](images/image13.png)

4.2 System prompt (use the exact rules below):

```
Rules:
1. Answer in JSON format only. 
2. You will get job position from user query and you will return only related information for that job position. 
3. Do NOT ask any question from user. They will give you a job position and you will return JSON only.
4. Ensure all fields are filled with appropriate data and avoid leaving any blank (e.g., 'not specified').
5. For the experience field, provide in-depth details and a comprehensive description. Do not just include a number or a short phrase. Describe the nature of the experience required for the job position (e.g., responsibilities, seniority level, or related skills)
```

4.3 User prompt (what the flow will send to the model):
```
job position:
```

You should see similar to this when the prompt is configured:

![prompt when configured](images/image14.png)

![Click Select Variable](images/image15.png)

![Select job_position](images/image16.png)

![Output when add job_position variable](images/image17.png)

---

5) Custom Output for the Generative Prompt

![Click open Output as Object](images/image18.png)

![Click add object definition](images/image19.png)

5.1 Change object output name to ```expected_criteria ``` with description ```expected_criteria align with job```

Use this JSON schema
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

![Select llama-4-maverick](images/image22.png)

![click edit test value](images/image23.png)

![set test values to Sales](images/image24.png)

![Click generate response](images/image25.png)

Output would be simliar like this.

![Output from generate response](images/image26.png)

---

6) Now Add new flow to upload 1st Candidate's Resume 

![select File upload](images/image27.png)

6.1 change name to  **Resume uploader1**

![change display name to Resume uploader1](images/image28.png)

---

7) Add a 1st Document Extractor  inside the User Activity<br>
  7.1 Drag a `Document Extractor` into the User Activity node.<br>
  7.2 Rename it to `Resume extractor1`.<br>
  7.3 Click Edit Fields<br>

![Drag 1st Document extractor to userflow](images/image29.png)

![change name to resume extractor1](images/image30.png)

![click edit fields](images/image31.png)

---
8) Download and Upload Sample Resumes<br>
  8.1 Download resumes from:
    -  `sample/jr-sale-resume.pdf` 
    -  `sample/sr-sale-resume.pdf`<br>

8.2 Upload `jr-sales-resume.pdf`

8.3 Click **Add Field**, name it as `name1` and configure the Field

![Click add field](images/image32.png)

![addtional configure for name1](images/image33.png)

Put Description as `Candidate name`

![example of description](images/image34.png)

And Click **Back Arrow** top left corner.

8.4 Click **Add Field**, names it as `skills1` and configure the Field

- For skills1 Using Description as
```
List all the skills mentioned, including both technical (hard) and interpersonal (soft) skills.
Provide the extracted skills in a clear and concise format, focusing on relevance to the job position.
```

8.5 Click **Add Field** names it as `experience1` and configure the Field

- For experience1 Using Description as
```
Include details on what the candidate has done in each position, specifying tasks, achievements, and responsibilities.
```

8.6 Open document dropdown and Click **Mangage documents** and upload file from ```sameple/sr-sale-resume.pdf```
![add more sample document](images/image36.png)

---
### Most of this part we repeat step 6 - 8 (receive canidate's resume and extract field)

9) Now Add new flow to upload 2nd Candidate's Resume 

![select File upload](images/image37.png)

9.1 change name to  **Resume uploader2**

---

10) Add a 2nd Document Extractor  inside the User Activity<br>
  10.1 Drag a `Document Extractor` into the User Activity node.<br>
  10.2 Rename it to `Resume extractor2`.<br>
  10.3 Click Edit Fields<br>

---
11) Download and Upload Sample Resumes<br>
  11.1 Download resumes from:
    -  `sample/jr-sale-resume.pdf` 
    -  `sample/sr-sale-resume.pdf`<br>

11.2 Upload `jr-sales-resume.pdf`

11.3 Click **Add Field**, name it as `name2` and configure the Field

![Click add field](images/image32.png)

![addtional configure for name1](images/image33.png)

Put Description as `Candidate name`

![example of description](images/image34.png)

And Click **Back Arrow** top left corner.

11.4 Click **Add Field**, names it as `skills2` and configure the Field

- For skills2 Using Description as
```
List all the skills mentioned, including both technical (hard) and interpersonal (soft) skills.
Provide the extracted skills in a clear and concise format, focusing on relevance to the job position.
```

11.5 Click **Add Field** names it as `experience2` and configure the Field

- For experience2 Using Description as
```
Include details on what the candidate has done in each position, specifying tasks, achievements, and responsibilities.
```

11.6 Open document dropdown and Click **Mangage documents** and upload file from ```sameple/sr-sale-resume.pdf```
![add more sample document](images/image36.png)

---

## Checkpoint: Current Workflow would be similar like this
![checkpoint_pic1](images/image38.png)
<br>
![checkpoint_pic2](images/image39.png)
<br>
![checkpoint_pic2](images/image40.png)

---

12. Drag Generative prompt into user flow name it as `scoring agent` Click Edit prompt settings<br>

![Drag latest Generative prompt](images/image41.png)

12.1  Click **Add input variable** and select variable type as **String**

![Click add input variable A](images/image42.png)

12.2 Name the input variable. Repeat this process for all required variables:

- `name1`  
  ![example input variable](images/image43.png)
- `skills1`
- `experience1`
- `name2`
- `skills2`
- `experience2`
- `expected_criteria_experience`
- `expected_criteria_skills`

12.3 For each variable:  
- Click **Add input variable**  
- Choose **String** as the type  
- Enter the variable name  
- Click **Save/Add**  

12.4 After adding all variables, your Generative Prompt input variables should include:

  ![all input variables](images/image44.png)

12.5 Add this into System prompt exactly
```
You are a resume comparison agent. Compare two candidates' resumes against the provided expected criteria. For each candidate, score them on a scale of 0-100, where 100 means the resume fully matches the criteria and 0 means no match. The comparison should be based on the following:
1. **Skills**: Evaluate the alignment of the candidate's skills with the job's requirements.
2. **Experience**: Assess the relevance and quality of the candidate's experience, including years of experience and the level of responsibility.
3. **Achievements**: Review the candidate's notable achievements that demonstrate their ability to succeed in the role.
4. **Other Key Factors**: Consider any other relevant factors such as certifications, leadership, and adaptability.

For each candidate, provide a detailed breakdown of the score in these sections:
- **Skills**: Explain how well the candidate’s skills align with the job’s requirements.
- **Experience**: Detail the relevance of their experience to the role, including the number of years and level of seniority.
- **Achievements**: Highlight significant accomplishments and their impact.
- **Other Key Factors**: Mention additional qualities or experiences that may impact their suitability for the job.

The output should include a **score** for each candidate along with **explanations** for each of the above categories, ensuring that both candidates are evaluated equally and fairly.

**OUTPUT MUST BE IN THAI**
```
 
12.6 Add user prompt as
```
resume1: candidate name={name1}, skills1={skills1}, experience1={experience1}
resume2: candidate name={name2}, skills2={skills2}, experience2={experience2}

expected_criteria: {expected_criteria_experience}, {expected_criteria_skills}
```

The output should be as

  ![User prompt](images/image45.png)

12.7 Change the Model to **llama-4-maverick-17b-128e-instruct-fp8**

  ![Change model Modelllama-4-maverick-17b-128e-instruct-fp8d](images/image46.png)

  This is lastest workflow then click **done** on top right corner

  ![lastest workflow](images/image47.png)

  ---
13 Change Model to **gemini-2.5-flash**

  ![change main model](images/image48.png)

14 Scroll down to **Beheavior Section** and add this instructions:
```
- You have to use tool named "resume_scoring_tool" whenever user ask about comparing candidate scoring or user want to upload resume for comparing. 
- You must answer in Thai.
```
  ![Behavior Section](images/image49.png)

  ---

  ### Testing
  
  - `ฉันอยากเปรียบเทียบ resume ของ candidateสองคน`
  ![Input1](images/image50.png)

- Answer with
```
A Senior Sales professional with a strong background in both B2B and B2C sales, equipped with
excellent communication skills essential for building client relationships and closing high-level deals.
Experience spans from managing existing clients to acquiring new ones across diverse markets.
```

- The Agent will allow you to upload first candidate resume  Upload ```jr-sales-resume.pdf```
- The Agent will allow you to upload second candidate resume  Upload ```sr-sales-resume.pdf```

## Example

  ![first example pic](images/image51.png)

  ![second example pic](images/image52.png)

  ![third example pic](images/image53.png)
