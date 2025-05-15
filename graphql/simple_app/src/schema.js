const typeDefs = `#graphql
  type Building {
    id: Int!
    name: String!
    address: String!
    totalEnergyConsumption: Float
    devices: [Device!]! @relationship(type: "HAS_DEVICE", direction: OUT)
    meters: [Meter!]! @relationship(type: "HAS_METER", direction: OUT)
  }

  type Device {
    id: Int!
    name: String!
    type: String!
    powerConsumption: Float
    status: String
    building: Building! @relationship(type: "HAS_DEVICE", direction: IN)
    readings: [Reading!]! @relationship(type: "HAS_READING", direction: OUT)
  }

  type Meter {
    id: Int!
    serialNumber: String!
    type: String!
    building: Building! @relationship(type: "HAS_METER", direction: IN)
    readings: [Reading!]! @relationship(type: "HAS_READING", direction: OUT)
  }

  type Reading {
    id: Int!
    value: Float!
    unit: String!
    device: Device @relationship(type: "HAS_READING", direction: IN)
    meter: Meter @relationship(type: "HAS_READING", direction: IN)
  }

  type Query {
    buildings: [Building!]!
    devices: [Device!]!
    meters: [Meter!]!
    readings: [Reading!]!
  }

  type Mutation {
    createBuilding(id: Int!, name: String!, address: String!): Building!
    createDevice(id: Int!, name: String!, type: String!, buildingId: ID!): Device!
    createMeter(id: Int!, serialNumber: String!, type: String!, buildingId: ID!): Meter!
    createReading(id: Int!, value: Float!, unit: String!, deviceId: ID, meterId: ID): Reading!
  }
`;

module.exports = typeDefs; 