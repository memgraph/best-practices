const { gql } = require('graphql-tag')

const typeDefs = gql`
  type Building @node {
    id: Int!
    name: String!
    address: String!
    totalEnergyConsumption: Float
    devices: [Device!]! @relationship(type: "HAS_DEVICE", direction: OUT)
    meters: [Meter!]! @relationship(type: "HAS_METER", direction: OUT)
  }

  type Device @node {
    id: Int!
    name: String!
    type: String!
    powerConsumption: Float
    status: String
    building: [Building!]! @relationship(type: "HAS_DEVICE", direction: IN)
    readings: [Reading!]! @relationship(type: "HAS_READING", direction: OUT)
  }

  type Meter @node {
    id: Int!
    serialNumber: String!
    type: String!
    building: [Building!]! @relationship(type: "HAS_METER", direction: IN)
    readings: [Reading!]! @relationship(type: "HAS_READING", direction: OUT)
  }

  type Reading @node {
    id: Int!
    value: Float!
    unit: String!
    device: [Device!]! @relationship(type: "HAS_READING", direction: IN)
    meter: [Meter!]! @relationship(type: "HAS_READING", direction: IN)
  }
`;

module.exports = typeDefs;
