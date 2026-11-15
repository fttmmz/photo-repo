"""Cloud Photo Repository: AWS architecture diagram.

Built with the free, open-source Python "diagrams" library (the same library the AWS Diagram MCP server used).
Re-create it on any computer:  pip install diagrams   (and install Graphviz from graphviz.org)
                               python architecture.py
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.general import Client, User
from diagrams.aws.integration import SNS
from diagrams.aws.management import Cloudformation, Cloudwatch
from diagrams.aws.network import APIGateway, CloudFront
from diagrams.aws.security import IAM, Cognito
from diagrams.aws.storage import S3

def icon(cls, label):
    """AWS icon with its label tight underneath, so arrows touch the icon instead of empty space."""
    lines = label.count("\n") + 1
    return cls(label, height=str(round(1.45 + 0.24 * lines, 2)), imagepos="tc", labelloc="b")


graph_attr = {
    "fontsize": "22",
    "fontname": "Helvetica",
    "pad": "0.4",
    "nodesep": "0.9",
    "ranksep": "1.3",
    "splines": "ortho",
    "newrank": "true",
}
node_attr = {"fontsize": "13", "fontname": "Helvetica"}
edge_attr = {"fontsize": "12", "fontname": "Helvetica Bold", "color": "#232F3E", "penwidth": "1.4"}


def step(n, **kw):
    """Numbered step badge on an arrow; the numbers are explained in the legend under the diagram."""
    return Edge(xlabel=" " + chr(0x2775 + n) + " ", fontcolor="#232F3E", fontsize="22", fontname="DejaVu Sans", **kw)


with Diagram(
    "Cloud Photo Repository: Serverless Architecture on AWS",
    filename="architecture-aws",
    outformat=["png", "svg"],
    direction="LR",
    show=False,
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    user = icon(User, "User")
    browser = icon(Client, "Web browser\n(web UI)")

    with Cluster("AWS Cloud: Europe (Stockholm) eu-north-1"):
        with Cluster("Web hosting"):
            cdn = icon(CloudFront, "Amazon CloudFront\n(HTTPS)")
            web = icon(S3, "Amazon S3\nweb UI bucket")

        with Cluster("Authentication"):
            cognito = icon(Cognito, "Amazon Cognito\nuser pool")

        with Cluster("API and application logic"):
            api = icon(APIGateway, "Amazon API Gateway\nCognito authorizer")
            api_fn = icon(Lambda, "AWS Lambda\nupload URL, list, get,\ndelete, search")

        with Cluster("Storage and data"):
            photos = icon(S3, "Amazon S3\nphoto bucket\noriginals + thumbnails")
            table = icon(Dynamodb, "Amazon DynamoDB\nphoto metadata")

        with Cluster("Image processing"):
            resize = icon(Lambda, "AWS Lambda\nresize (thumbnails)")

        with Cluster("Security, monitoring and deployment"):
            iam = icon(IAM, "AWS IAM\nrole per Lambda")
            logs = icon(Cloudwatch, "Amazon CloudWatch\nlogs, metrics, alarms")
            alerts = icon(SNS, "Amazon SNS\nemail alerts")
            iac = icon(Cloudformation, "AWS CloudFormation\n(infrastructure as code)")

    user >> browser
    browser >> step(1) >> cdn >> web
    browser >> step(2) >> cognito
    browser >> step(3) >> api
    api >> Edge(style="dashed") >> cognito
    api >> step(4) >> api_fn
    api_fn >> step(5) >> table
    api_fn >> Edge(style="dashed") >> photos
    browser >> step(6) >> photos
    photos >> step(7) >> resize
    resize >> step(8) >> table
    logs >> Edge(label=" alarm ") >> alerts
    # keep the security/monitoring icons in one row
    iam >> Edge(style="invis") >> logs
    alerts >> Edge(style="invis") >> iac
